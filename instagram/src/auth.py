import functools
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

from . import api
from . import database
from . import return_codes
from .logging import BASE_LOGGER

bp = Blueprint("auth", __name__, url_prefix="/auth")

MIN_PASSWORD_LEN = 10
LOGGER = BASE_LOGGER.getChild(__name__)


def check_password_complexity(pw):
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
        user_id = request.form["user_id"].strip()
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        LOGGER.info(
            f"Request to register user '{user_id}' with first name "
            f"'{first_name}' and last name '{last_name}'"
        )
        if "avatar" in request.files:
            avatar_data = request.files["avatar"].read()
        else:
            avatar_data = None
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
            if avatar_data is not None and len(avatar_data) > 0:
                avatar_id = api.put_avatar_image(avatar_data)
            else:
                avatar_id = None
            pw_hash = generate_password_hash(password_1)
            rcode = api.create_user(
                user_id, first_name, last_name, pw_hash, avatar_id,
            )
            if rcode is return_codes.USER_EXISTS:
                error = f"User ID '{user_id}' is already taken"
            else:
                LOGGER.info(f"Registered user '{user_id}'")
                return redirect(url_for("auth.login"))

        flash(error)
        LOGGER.error(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        user_id = request.form["user_id"].strip()
        password = request.form["password"]

        user_info = database.get_user_info(user_id)
        if not user_info:
            error = f"Incorrect user '{user_id}'"
            flash(error)
            LOGGER.error(error)
            return render_template("auth/login.html")

        if database.user_is_locked(user_id):
            error = "User account is locked for 15 minutes"
            flash(error)
            LOGGER.error(error)
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
            session["avatar_url"] = api.get_avatar_url(user_info["avatar_id"])
            return redirect(url_for("index"))

        flash(error)
        LOGGER.error(error)

    return render_template("auth/login.html")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user_id = None
    else:
        g.user_id = user_id
        g.avatar_url = session["avatar_url"]


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def login_required(view):
    @functools.wraps(view)
    def wrapper(**kwargs):
        if g.user_id is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapper
