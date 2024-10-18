import uuid

from flask import Blueprint, render_template, redirect, url_for, session, flash
from flask_login import login_user, login_required, logout_user, current_user
from app import db, oauth
from app.models.user import User

auth = Blueprint("auth", __name__)


@auth.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@auth.route("/login/google")
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    nonce = uuid.uuid4().hex + uuid.uuid1().hex
    session["google_auth_nonce"] = nonce
    redirect_uri = url_for("auth.google_authorize", _external=True)

    return oauth.google.authorize_redirect(
        redirect_uri,
        nonce=nonce,
        prompt="select_account",
        access_type="offline",
    )


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

    if "refresh_token" in token:
        user.google_refresh_token = token["refresh_token"]

    db.session.commit()

    login_user(user)
    return redirect(url_for("main.dashboard"))


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
