import os
import secrets
from urllib.parse import quote_plus

import requests
from flask import (
    abort,
    Flask,
    g,
    render_template,
    request,
    session,
)

APP_HOST = os.getenv("APP_URL", "127.0.0.1")
APP_PORT = os.getenv("APP_PORT", 5000)
APP_URL = f"{APP_HOST}:{APP_PORT}"
DEFAULT_USER = "anonymous"
TTL_TO_HOURS = {
    "1h": 1,
    "1d", 24,
    "1w", 24 * 7,
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
        user_texts = []

        if request.method == "POST":
            username = session.get("username", DEFAULT_USER)
            text_title = request.form["text-title"]
            text_body = request.form["text-body"]
            ttl = TTL_TO_HOURS[request.form["ttl"]]

            id_service_host = os.getenv("ID_SERVICE_HOST")
            id_service_port = os.getenv("ID_SERVICE_PORT")
            text_id = requests.get(
                f"http://{id_service_host}:{id_service_port}/get-id"
            ).json()["id"]

            metadata_client.store_text(text_id, text_body, username, ttl)
            msg = f"Stored text at {APP_URL}/{text_id}"

        if g.user:
            user_texts = metadata_client.get_texts_by_user(g.user["_id"])
            for ut in user_texts:
                u["url"] = f"{APP_URL}/{ut['text_id']}"
                u["created_on"] = u["creation_date"].strftime(
                    "%m/%d/%Y %H:%M:%S"
                )
                u["ttl"] = u["ttl"].strftime("%m/%d/%Y %H:%M:%S")

        return render_template("index.html", message=msg, mytexts=user_texts)

    @app.route("/<text_id>")
    def text(text_id):
        text_body = object_store.get_text(text_id)
        if text_body is None:
            abort(404)
        return render_template("text.html", text_body=text_body)

    from . import auth
    app.register_blueprint(auth.bp)

    return app
