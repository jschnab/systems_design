import string

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

MIN_PASSWORD_LEN = 10


def check_password_complexity(pw):
    """
    Expect a minimum length of 10 characters and at least one of each:

    * lowercase ASCII letter
    * uppercase ASCII letter
    * digit
    * punctuation character

    If complexity requirements are met, return ``True`` else ``False``.
    """
    if len(pw) < MIN_PASSWORD_LEN:
        return False
    has_lower = has_upper = has_digit = has_punct = False
    for char in pw:
        has_lower |= char.islower()
        has_upper |= char.isupper()
        has_digit |= char.isnumeric()
        has_punct |= char in string.punctuation
    return all([has_lower, has_upper, has_digit, has_punct])


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        user_id = request.form["user_id"]
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        password_1 = request.form["password_1"]
        password_2 = request.form["password_2"]

        error = None
        if user_id is None:
            error = "User ID is required"
        elif password_1 is None:
            error = "Password is required"
        elif check_password_complexity(password_1) is False:
            error = "Password does not meet complexity requirements"
        elif password_1 != password_2:
            error = "Passwords do not match"

        if error is None:
            pw_hash = generate_password_hash(password_1)
            rcode = database.create_user(
                user_id, firstname, lastname, pw_hash,
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

        user_info = database.get_user(user_id)
        if user_info is None:
            flash("Incorrect user")
            return render_template("auth/login.html")

        if database.user_is_locked(user_id):
            flash("User account is locked for 15 minutes")
            return render_template("auth/login.html")

        error = None
        success = True
        if not check_password_hash(user_info["password"], password):
            error = "Incorrect password"
            success = False

        user_ip = request.environ.get(
            "HTTP_X_REAL_IP", request.remote_addr
        )
        database.record_user_connect(
            user_id=user_id,
            user_ip=user_ip,
            success=success,
        )

        if error is None:
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
