import secrets
from datetime import datetime, timedelta

from flask import (
    abort,
    Flask,
    render_template,
    request,
    session,
)

from . import alias_client
from . import database
from . import object_store
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

            text_id = alias_client.get_id()
            if text_id is None:
                msg = "Something went wrong, try again later"

            else:
                object_store.put_text(key=text_id, text_body=text_body)
                database.put_text_metadata(
                    text_id=text_id,
                    user_id=user_id,
                    creation_timestamp=creation_timestamp,
                    expiration_timestamp=expiration_timestamp,
                )
                msg = f"Stored text at {APP_URL}/text/{text_id}"

        return render_template("index.html", message=msg)

    @app.route("/text/<text_id>")
    def text(text_id):
        text_body = object_store.get_text(text_id)
        if text_body is None:
            abort(404)
        return render_template("text.html", text_body=text_body)

    from . import auth

    app.register_blueprint(auth.bp)

    return app
