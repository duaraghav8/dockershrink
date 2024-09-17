import os
import uuid

from flask import Flask, jsonify, request, redirect, url_for, render_template, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta
import jwt
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

oauth = OAuth(app)

# OAuth configuration
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

github = oauth.register(
    name='github',
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    api_token = db.Column(db.String(64), unique=True, index=True)
    openai_api_key = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_api_token(self):
        self.api_token = secrets.token_hex(32)
        db.session.commit()
        return self.api_token


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login/google')
def google_login():
    nonce = uuid.uuid4().hex + uuid.uuid1().hex
    session['google_auth_nonce'] = nonce
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)


@app.route('/login/github')
def github_login():
    redirect_uri = url_for('github_authorize', _external=True)
    return github.authorize_redirect(redirect_uri)


@app.route('/authorize/google')
def google_authorize():
    token = oauth.google.authorize_access_token()

    nonce = session.pop('google_auth_nonce', None)
    if nonce is None:
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    try:
        userinfo = oauth.google.parse_id_token(token)
        email = userinfo['email']

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email)
            db.session.add(user)
            db.session.commit()

        login_user(user)
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Authentication error: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


@app.route('/authorize/github')
def github_authorize():
    token = github.authorize_access_token()
    resp = github.get('user')
    user_info = resp.json()
    email = user_info['email']
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/api/v1/generate_token', methods=['POST'])
@login_required
def generate_token():
    token = current_user.generate_api_token()
    return jsonify({'token': token})


@app.route('/api/v1/store_openai_key', methods=['POST'])
@login_required
def store_openai_key():
    data = request.get_json()
    openai_key = data.get('openai_key')
    if not openai_key:
        return jsonify({'error': 'OpenAI API key is required'}), 400
    current_user.openai_api_key = openai_key
    db.session.commit()
    return jsonify({'message': 'OpenAI API key stored successfully'})


@app.route('/api/v1/user/<int:id>')
def get_user(id):
    # Check for API token in headers
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


if __name__ == '__main__':
    app.run(debug=True)
