from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.service.optimizer import Optimizer
from app.models.user import User

api = Blueprint('api', __name__)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_token = request.headers.get('Authorization')
        if not api_token:
            return jsonify({'error': 'API token is missing'}), 401

        user = User.query.filter_by(api_token=api_token).first()
        if not user:
            return jsonify({'error': 'Invalid API token'}), 401

        return f(user, *args, **kwargs)

    return decorated


@api.route('/generate_token', methods=['POST'])
@login_required
def generate_token():
    token = current_user.generate_api_token()
    return jsonify({'token': token})


@api.route('/store_openai_key', methods=['POST'])
@login_required
def store_openai_key():
    data = request.get_json()

    openai_key = data.get('openai_key')
    if not openai_key:
        return jsonify({'error': 'OpenAI API key is required'}), 400

    current_user.set_openai_api_key(openai_key)
    return jsonify({'message': 'OpenAI API key stored successfully'})


@api.route('/generate', methods=['POST'])
@token_required
def generate(user):
    return jsonify({
        "Dockerfile": "",
        ".dockerignore": ""
    })


@api.route('/optimize', methods=['POST'])
@token_required
def optimize(user):
    data = request.get_json()
    if not data:
        return jsonify(
            {'error': 'No data provided, at least Dockerfile must be provided'}
        ), 400

    dockerfile = data.get('Dockerfile')
    if not dockerfile:
        return jsonify({'error': 'Dockerfile was not provided'}, 400)

    dockerignore = data.get('.dockerignore')
    package_json = data.get('package.json')

    optimizer = Optimizer(
        dockerfile=dockerfile,
        dockerignore=dockerignore,
        package_json=package_json,
        openai_api_key=user.get_openai_api_key(),
    )

    try:
        resp = optimizer.optimize()
    except Exception as e:
        return jsonify(
            {'error': f"An error occurred while optimizing the project: {e}"}
        ), 400

    # The API response will be:
    #  A JSON object that contains all suggestions + metadata (file name, line no., etc.)
    #  All the files that were modified.
    #  If a file was supplied to the api but not modified by the analyser, we don't send it in response.

    return jsonify(resp)
