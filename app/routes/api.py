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


# TODO: remove this api route
# It is useful only to verify that the whole token authorization thing works
@api.route('/user/<int:id>')
def get_user(id):
    api_token = request.headers.get('Authorization')
    if not api_token:
        return jsonify({'error': 'API token is missing'}), 401

    user = User.query.filter_by(api_token=api_token).first()
    if not user:
        return jsonify({'error': 'Invalid API token'}), 401

    requested_user = User.query.get(id)
    if not requested_user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': requested_user.id,
        'email': requested_user.email
    })
