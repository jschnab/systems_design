import functools

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

from . import couchdb

bp = Blueprint("auth", __name__, url_prefix="/auth")
db_client = couchdb.Client()


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form["username"]
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        password = request.form["password"]

        error = None
        if not username:
            error = "Username is required"
        elif not password:
            error = "Password is required"

        if error is None:
            print("registering user")
            result = db_client.register_user(
                username,
                firstname,
                lastname,
                generate_password_hash(password),
            )
            if result is not None:
                print("an error happened:", result)
                error = result
            else:
                print("successfully registered user")
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        error = None
        user = db_client.get_user(username)
        if user is None:
            error = "Incorrect username"
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password"

        if error is None:
            db_client.update_user_last_login(username)
            session.clear()
            session["username"] = username
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@bp.before_app_request
def load_logged_in_user():
    username = session.get("username")
    if username is None:
        g.user = None
    else:
        g.user = db_client.get_user(username)


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
