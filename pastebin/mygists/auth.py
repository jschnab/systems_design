import functools
from datetime import datetime

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from . import database
from . import return_codes

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        user_id = request.form["user_id"]
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        password = generate_password_hash(request.form["password"])

        error = None
        if user_id is None:
            error = "User ID is required"
        elif password is None:
            error = "Password is required"

        if error is None:
            now = datetime.now()
            rcode = database.create_user(
                user_id, firstname, lastname, now, password,
            )
            if rcode is return_codes.USER_EXISTS:
                error = f"User ID '{user_id}' is already taken"
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]
        error = None

        user_info = database.get_user(user_id)
        if user_info is None:
            error = "Incorrect user"
        elif not check_password_hash(user_info["password"], password):
            error = "Incorrect password"

        if error is None:
            now = datetime.now()
            database.update_user_last_connection(user_id, now)
            session.clear()
            session["user_id"] = user_id
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = database.get_user(user_id)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view
