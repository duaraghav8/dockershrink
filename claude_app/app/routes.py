import uuid

from flask import Blueprint, render_template, redirect, url_for, jsonify, request, session, flash
from flask_login import login_user, login_required, current_user, logout_user
from app import db, oauth
from app.models import User

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
api = Blueprint('api', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)


@auth.route('/login')
def login():
    return render_template('login.html')


@auth.route('/login/google')
def google_login():
    nonce = uuid.uuid4().hex + uuid.uuid1().hex
    session['google_auth_nonce'] = nonce
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)


@auth.route('/login/github')
def github_login():
    redirect_uri = url_for('auth.github_authorize', _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@auth.route('/authorize/google')
def google_authorize():
    token = oauth.google.authorize_access_token()

    nonce = session.pop('google_auth_nonce', None)
    if nonce is None:
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    userinfo = oauth.google.parse_id_token(token, nonce=nonce)
    email = userinfo['email']

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for('main.dashboard'))


@auth.route('/authorize/github')
def github_authorize():
    token = oauth.github.authorize_access_token()
    resp = oauth.github.get('user')
    user_info = resp.json()
    email = user_info['email']
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for('main.dashboard'))


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


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
