from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.user import User

api = Blueprint('api', __name__)


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


@api.route('/analyse_project', methods=['POST'])
def analyse_project():
    # Ensure that the request has a valid api token that belongs to an active user in the DB
    api_token = request.headers.get('Authorization')
    if not api_token:
        return jsonify({'error': 'API token is missing'}), 401

    user = User.query.filter_by(api_token=api_token).first()
    if not user:
        return jsonify({'error': 'Invalid API token'}), 401

    # Get the user's openaiapi key from db. The key is optional
    #  user.get_openai_api_key()

    return jsonify({"ok": "ok"})

    # Get the Dockerfile, .dockerignore (optional), package.json (optional) files from post data
    # Invoke the analyser and provide it with all the data
    # Collect response back from analyser
    # The API response will be:
    #  A JSON object that contains all suggestions + metadata (file name, line no., etc.)
    #  All the files that were modified.
    #  If a file was supplied to the api but not modified by the analyser, we don't send it in response.
