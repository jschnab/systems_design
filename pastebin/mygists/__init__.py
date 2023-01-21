import secrets
from datetime import datetime, timedelta

from flask import (
    abort,
    flash,
    Flask,
    render_template,
    request,
    session,
)

from . import api
from . import database
from . import object_store
from .config import config

APP_URL = f"{config['app']['host']}:{config['app']['port']}"
DEFAULT_USER = config["app"]["default_user"]
TTL_TO_HOURS = {
    "1h": 1,
    "1d": 24,
    "1w": 24 * 7,
    "1m": 24 * 30,
    "1y": 24 * 365,
}


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = secrets.token_hex()

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    @app.route("/", methods=("GET", "POST"))
    def index():
        msg = None

        if request.method == "POST":
            user_id = session.get("user_id", DEFAULT_USER)
            text_body = request.form["text-body"]
            ttl = TTL_TO_HOURS[request.form["ttl"]]
            creation_timestamp = datetime.now()
            expiration_timestamp = creation_timestamp + timedelta(hours=ttl)

            if user_id == DEFAULT_USER:
                user_ip = request.environ.get(
                    "HTTP_X_REAL_IP",
                    request.remote_addr
                )

            text_id = api.store_text(
                text_body=text_body,
                user_id=user_id,
                creation_timestamp=creation_timestamp,
                expiration_timestamp=expiration_timestamp,
            )
            msg = f"Stored text at {APP_URL}/text/{text_id}"

        return render_template("index.html", message=msg)

    @app.route("/text/<text_id>")
    def get_text(text_id):
        text_body = object_store.get_text(text_id)
        if text_body is None:
            abort(404)
        return render_template("text.html", text_body=text_body)

    @app.route("/delete-text", methods=("POST",))
    def delete_text():
        if request.method == "POST":
            text_id = request.form["text-id"]
            api.delete_text(text_id=text_id)
        return "OK"

    @app.route("/mytexts")
    def user_texts():
        user_id = session.get("user_id")
        if user_id is None:
            flash("Please log in to see your saved texts")
            return render_template("index.html")

        texts = database.get_texts_by_user(user_id)
        return render_template(
            "user_texts.html", mytexts=texts, app_url=APP_URL,
        )

    from . import auth

    app.register_blueprint(auth.bp)

    return app
