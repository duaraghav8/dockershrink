import os
from flask import Flask, redirect, url_for, session, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from cryptography.fernet import Fernet
from flask_cors import CORS
import hashlib

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['SESSION_COOKIE_SECURE'] = True  # Use secure cookies in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session lifetime in seconds (1 hour)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
oauth = OAuth(app)
CORS(app)

# Set up encryption for storing user secrets
# encryption_key = os.getenv('ENCRYPTION_KEY')
encryption_key = Fernet.generate_key()
fernet = Fernet(encryption_key)

# OAuth Config
oauth.register(
    'google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    client_kwargs={'scope': 'openid profile email'}
)

oauth.register(
    'github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    authorize_url='https://github.com/login/oauth/authorize',
    access_token_url='https://github.com/login/oauth/access_token',
    client_kwargs={'scope': 'user:email'}
)


# PostgreSQL User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    oauth_id = db.Column(db.String(150), unique=True)
    tokens = db.Column(db.Text)
    api_token_hash = db.Column(db.String(255), nullable=True)
    secret_string = db.Column(db.String(500), nullable=True)


# Database Initialization
with app.app_context():
    db.create_all()


### OAuth Routes


@app.route('/api/v1/login/google')
def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/api/v1/login/github')
def github_login():
    redirect_uri = url_for('github_authorize', _external=True)
    return oauth.github.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def google_authorize():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token)
    return handle_oauth_login(user_info, 'google')

@app.route('/authorize/github')
def github_authorize():
    token = oauth.github.authorize_access_token()
    user_info = oauth.github.get('user')
    return handle_oauth_login(user_info.json(), 'github')

def handle_oauth_login(user_info, provider):
    email = user_info['email']

    # Check if user exists in DB
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, oauth_id=user_info['id'])
        db.session.add(user)
        db.session.commit()

    # Set session
    session['user_id'] = user.id
    return redirect('/dashboard')


### Dashboard & Token Generation

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('google_login'))

    user = User.query.get(session['user_id'])
    return f"Welcome to your dashboard, {user.email}!"

@app.route('/api/v1/token', methods=['POST'])
def generate_token():
    if 'user_id' not in session:
        return jsonify({"error": "User not authenticated"}), 401

    user = User.query.get(session['user_id'])
    access_token = create_access_token(identity=user.id)

    # Hash the API token and store in the DB
    token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    user.api_token_hash = token_hash
    db.session.commit()

    return jsonify(access_token=access_token)


### Storing Secrets

@app.route('/api/v1/store_secret', methods=['POST'])
@jwt_required()
def store_secret():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    secret_string = request.json.get('secret_string')
    encrypted_secret = fernet.encrypt(secret_string.encode())

    user.secret_string = encrypted_secret
    db.session.commit()

    return jsonify({"message": "Secret stored successfully"})


### API Routes

@app.route('/api/v1/user/<int:id>', methods=['GET'])
@jwt_required()
def get_user(id):
    current_user_id = get_jwt_identity()

    if current_user_id != id:
        return jsonify({"error": "Unauthorized access"}), 403

    user = User.query.get(id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"id": user.id, "email": user.email})


### Heroku App Entry Point

if __name__ == "__main__":
    app.run(debug=True)
