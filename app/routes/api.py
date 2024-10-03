from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from openai import OpenAI

from app.service.ai import AIService
from app.service.dockerfile.dockerfile import Dockerfile
from app.service.dockerignore import Dockerignore
from app.service.package_json import PackageJSON
from app.service.project import Project
from app.models.user import User

api = Blueprint("api", __name__)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_token = request.headers.get("Authorization")
        if not api_token:
            return jsonify({"error": "API token is missing"}), 401

        user = User.query.filter_by(api_token=api_token).first()
        if not user:
            return jsonify({"error": "Invalid API token"}), 401

        return f(user, *args, **kwargs)

    return decorated


@api.route("/generate_token", methods=["POST"])
@login_required
def generate_token():
    token = current_user.generate_api_token()
    return jsonify({"token": token})


@api.route("/store_openai_key", methods=["POST"])
@login_required
def store_openai_key():
    data = request.get_json()

    openai_key = data.get("openai_key")
    if not openai_key:
        return jsonify({"error": "OpenAI API key is required"}), 400

    current_user.set_openai_api_key(openai_key)
    return jsonify({"message": "OpenAI API key stored successfully"})


@api.route("/generate", methods=["POST"])
@token_required
def generate(user):
    """
    Generates new Docker image definition for the given project, focused on minimizing size.
    This will create new Dockerfile, .dockerignore and any other assets applicable.
    """
    data = request.get_json()
    if not data:
        return (
            jsonify(
                {"error": "No data provided. At least package.json must be provided."}
            ),
            400,
        )

    package_json = data.get("package.json")
    if not package_json:
        return jsonify({"error": "package.json was not provided"}), 400

    ai = None
    ai_access_key = user.get_openai_api_key()
    if ai_access_key:
        ai = AIService(ai_access_key)

    project = Project(package_json=PackageJSON(package_json))
    try:
        dockerfile, dockerignore = project.generate_docker_image_definition(ai)
    except Exception as e:
        return (
            jsonify(
                {"error": f"An error occurred while generating image definition: {e}"}
            ),
            400,
        )

    # TODO: Optimise the generated docker assets
    #  One way is to add the dockerfile, .dockerignore into a new project and run optimize() on it
    #  p2 = Project(dockerfile, dockerignore)
    #  resp = p2.optimize()
    #  return resp assets
    # In this case, the generate method only needs to generate a dockerfile with basic rules.
    # Other rules are taken care of by optimize()

    return jsonify(
        {
            "Dockerfile": dockerfile,
            ".dockerignore": dockerignore,
        }
    )


@api.route("/optimize", methods=["POST"])
@token_required
def optimize(user):
    data = request.get_json()
    if not data:
        return (
            jsonify(
                {"error": "No data provided. At least Dockerfile must be provided."}
            ),
            400,
        )

    dockerfile = data.get("Dockerfile")
    if not dockerfile:
        return (
            jsonify(
                {"error": "No Dockerfile provided"},
            ),
            400,
        )

    dockerignore = data.get(".dockerignore")
    package_json = data.get("package.json")

    ai = None
    ai_access_key = user.get_openai_api_key()
    if ai_access_key:
        openai_client = OpenAI(api_key=ai_access_key)
        ai = AIService(openai_client)

    project = Project(
        dockerfile=Dockerfile(dockerfile),
        dockerignore=Dockerignore(dockerignore),
        package_json=PackageJSON(package_json),
    )
    try:
        resp = project.optimize_docker_image(ai)
    except Exception as e:
        return (
            jsonify({"error": f"An error occurred while optimizing the project: {e}"}),
            400,
        )

    return jsonify(resp)
