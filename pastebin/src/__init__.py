import os
import secrets
from datetime import datetime

from quart import (
    abort,
    flash,
    Quart,
    render_template,
    request,
    send_from_directory,
    session,
)

from . import api
from . import auth
from . import database
from .config import config

APP_URL = config["app"]["url"]
TEXT_MIN_CHAR = 110
TEXT_MAX_CHAR = 512000


def create_app():
    app = Quart(__name__)
    app.secret_key = secrets.token_hex()

    @app.route("/", methods=("GET", "POST"))
    async def index():

        if request.method == "GET":
            return await render_template("index.html")

        # request.form is a coroutine
        request_form = await request.form

        if len(request_form["text-body"]) < TEXT_MIN_CHAR:
            return await render_template(
                "index.html",
                message=f"Text should be at least {TEXT_MIN_CHAR} characters",
            )

        if len(request_form["text-body"]) > TEXT_MAX_CHAR:
            return await render_template(
                "index.html",
                message=f"Text should be less than {TEXT_MAX_CHAR} characters",
            )

        user_id = session.get("user_id", config["app"]["default_user"])
        user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if await api.user_exceeded_quota(user_id, user_ip):
            if user_id == config["app"]["default_user"]:
                quota = config["app"]["texts_quota_anonymous"]
            else:
                quota = config["app"]["texts_quota_user"]
            msg = (
                f"User '{user_id}' stored more than {quota} texts during the "
                "past day, come back later"
            )
        else:
            text_id = await api.put_text(
                text_body=(await request.form)["text-body"],
                user_id=user_id,
                user_ip=user_ip,
                ttl=(await request.form)["ttl"],
            )
            msg = f"Stored text at {APP_URL}/text/{text_id}"

        return await render_template("index.html", message=msg)

    @app.route("/text/<text_id>")
    async def get_text(text_id):
        text_body = await api.get_text(text_id)
        if text_body is None:
            abort(404)
        return await render_template("text.html", text_body=text_body)

    @app.route("/delete-text", methods=("POST",))
    async def delete_text():
        text_id = (await request.form)["text-id"]
        user_id = await database.get_user_by_text(text_id)
        logged_user = session.get("user_id")
        if logged_user is None or user_id != logged_user:
            abort(403)
        await api.delete_text(
            text_id=text_id, deletion_timestamp=datetime.now()
        )
        return "OK"

    @app.route("/mytexts")
    async def user_texts():
        user_id = session.get("user_id")
        if user_id is None:
            await flash("Please log in to see your saved texts")
            return await render_template("index.html")

        texts = await database.get_texts_by_user(user_id)
        return await render_template(
            "user_texts.html",
            mytexts=texts,
            app_url=APP_URL,
        )

    @app.route("/favicon.ico")
    async def favicon():
        return await send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    app.register_blueprint(auth.bp)

    return app
