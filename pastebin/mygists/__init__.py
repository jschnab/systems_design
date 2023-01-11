import secrets
from datetime import datetime, timedelta

import requests
from flask import (
    abort,
    Flask,
    render_template,
    request,
    session,
)

from . import database
from . import s3
from .config import config

APP_URL = f"{config['app']['host']}:{config['app']['port']}"
DEFAULT_USER = "anonymous"
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

            id_service_host = config["alias_service"]["host"]
            id_service_port = config["alias_service"]["port"]
            text_id = requests.get(
                f"http://{id_service_host}:{id_service_port}/get-alias"
            ).json()["alias"]

            try:
                database.put_text(
                    text_id=text_id,
                    text_body=text_body,
                    user_id=user_id,
                    creation_timestamp=creation_timestamp,
                    expiration_timestamp=expiration_timestamp,
                )
                msg = f"Stored text at {APP_URL}/{text_id}"
            except Exception:
                msg = "Something went wrong, please try again"

        return render_template("index.html", message=msg)

    @app.route("/<text_id>")
    def text(text_id):
        text_body = s3.get_text(text_id)
        if text_body is None:
            abort(404)
        return render_template("text.html", text_body=text_body)

    from . import auth

    app.register_blueprint(auth.bp)

    return app
