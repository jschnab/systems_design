import string

from quart import (
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
from .config import config

try:
    # Some Python installations do not have scrypt, but all have pbkdf2.
    from hashlib import scrypt  # noqa: F401

    HASH_METHOD = "scrypt"
except ImportError:
    HASH_METHOD = "pbkdf2"

MIN_PASSWORD_LEN = 10
DEFAULT_USER = config["app"]["default_user"]

bp = Blueprint("auth", __name__, url_prefix="/auth")


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
async def register():
    if request.method == "POST":
        request_form = await request.form

        user_id = request_form["user_id"]
        if user_id == DEFAULT_USER:
            await flash(f"User ID '{DEFAULT_USER}' is already taken")
            return redirect(url_for("auth.register"))

        firstname = request_form["firstname"]
        lastname = request_form["lastname"]
        password_1 = request_form["password_1"]
        password_2 = request_form["password_2"]

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
            pw_hash = generate_password_hash(password_1, method=HASH_METHOD)
            rcode = await database.create_user(
                user_id,
                firstname,
                lastname,
                pw_hash,
            )
            if rcode is return_codes.USER_EXISTS:
                error = f"User ID '{user_id}' is already taken"
            else:
                await flash(f"User '{user_id}' successfully created!")
                return redirect(url_for("auth.login"))

        await flash(error)

    return await render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
async def login():
    if request.method == "POST":
        request_form = await request.form

        user_id = request_form["user_id"]
        if user_id == config["app"]["default_user"]:
            await flash("Incorrect user")
            return redirect(url_for("auth.login"))

        password = request_form["password"]

        user_info = await database.get_user(user_id)
        if user_info is None:
            await flash("Incorrect user")
            return redirect(url_for("auth.login"))

        if await database.user_is_locked(user_id):
            await flash("User account is locked for 15 minutes")
            return redirect(url_for("auth.login"))

        error = None
        success = True
        if not check_password_hash(user_info["password"], password):
            error = "Incorrect password"
            success = False

        user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        await database.record_user_connect(
            user_id=user_id,
            user_ip=user_ip,
            success=success,
        )

        if error:
            await flash(error)
            return redirect(url_for("auth.login"))

        session.clear()
        session["user_id"] = user_id
        return redirect(url_for("index"))

    return await render_template("auth/login.html")


@bp.before_app_request
async def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = await database.get_user(user_id)


@bp.route("/logout")
async def logout():
    session.clear()
    return redirect(url_for("index"))
