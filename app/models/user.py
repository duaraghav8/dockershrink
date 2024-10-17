from app import db
from flask_login import UserMixin
import secrets


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    api_token = db.Column(db.String(64), unique=True, index=True)
    openai_api_key = db.Column(db.String(256))

    def generate_api_token(self) -> str:
        self.api_token = secrets.token_hex(32)
        db.session.commit()
        return self.api_token

    def get_api_token(self) -> str:
        return self.api_token

    def set_openai_api_key(self, key: str) -> str:
        self.openai_api_key = key
        db.session.commit()
        return self.openai_api_key

    def get_openai_api_key(self) -> str:
        return self.openai_api_key
