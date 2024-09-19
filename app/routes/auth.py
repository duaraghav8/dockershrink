import uuid

from flask import Blueprint, render_template, redirect, url_for, session, flash
from flask_login import login_user, login_required, logout_user
from app import db, oauth
from app.models.user import User

auth = Blueprint("auth", __name__)


@auth.route("/login")
def login():
    return render_template("login.html")


@auth.route("/login/google")
def google_login():
    nonce = uuid.uuid4().hex + uuid.uuid1().hex
    session["google_auth_nonce"] = nonce
    redirect_uri = url_for("auth.google_authorize", _external=True)
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)


@auth.route("/login/github")
def github_login():
    redirect_uri = url_for("auth.github_authorize", _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@auth.route("/authorize/google")
def google_authorize():
    token = oauth.google.authorize_access_token()

    nonce = session.pop("google_auth_nonce", None)
    if nonce is None:
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for("auth.login"))

    userinfo = oauth.google.parse_id_token(token, nonce=nonce)
    email = userinfo["email"]

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("main.dashboard"))


@auth.route("/authorize/github")
def github_authorize():
    token = oauth.github.authorize_access_token()
    resp = oauth.github.get("user")
    user_info = resp.json()
    email = user_info["email"]
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for("main.dashboard"))


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
