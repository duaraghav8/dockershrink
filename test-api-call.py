import openai
from flask import Blueprint, jsonify, request
from openai import OpenAI

from app.service.ai import AIService
from app.service.dockerfile.dockerfile import Dockerfile
from app.service.dockerignore import Dockerignore
from app.service.package_json import PackageJSON
from app.service.project import Project

api = Blueprint("api", __name__)


@api.route("/optimize", methods=["POST"])
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

    # TODO: Un-comment below line once we allow the user to store openai api key with us
    # ai_access_key = user.get_openai_api_key()
    ai_access_key = data.get("openai_api_key")

    ai = None
    if ai_access_key:
        openai_client = OpenAI(api_key=ai_access_key)
        ai = AIService(openai_client)

    pj = None
    package_json = data.get("package.json")
    if package_json is not None:
        if not type(package_json) == dict:
            err = {
                "error": f"package.json must be supplied as a JSON object, current type is {type(package_json)}",
            }
            return jsonify(err), 400

        pj = PackageJSON(package_json)

    project = Project(
        dockerfile=Dockerfile(dockerfile),
        dockerignore=Dockerignore(dockerignore),
        package_json=pj,
    )

    try:
        resp = project.optimize_docker_image(ai)
    except openai.APIStatusError as e:
        return (
            jsonify({"error": f"Request to OpenAI API failed: {e.body}"}),
            e.status_code,
        )
    except openai.APIError as e:
        return jsonify({"error": f"Request to OpenAI API failed: {e}"}), 500
    except Exception as e:
        return (
            jsonify({"error": f"An error occurred while optimizing the project: {e}"}),
            400,
        )

    return jsonify(resp)
