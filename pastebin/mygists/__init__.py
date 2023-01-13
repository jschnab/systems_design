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

from . import alias_client
from . import database
from . import return_codes
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

            rcode, text_id = alias_client.get_id()
            if rcode != return_codes.OK:
                msg = "Something went wrong, please try again"

            else:
                rcode, response = s3.put_text(key=text_id, text_body=text_body)
                if rcode != return_codes.OK:
                    msg = "Something went wrong, please try again"

                else:
                    rcode, retval = database.put_text_metadata(
                        text_id=text_id,
                        user_id=user_id,
                        creation_timestamp=creation_timestamp,
                        expiration_timestamp=expiration_timestamp,
                    )
                    if rcode != return_codes.OK:
                        msg = "Something went wrong, please try again"
                    else:
                        msg = f"Stored text at {APP_URL}/text/{text_id}"

        return render_template("index.html", message=msg)

    @app.route("/text/<text_id>")
    def text(text_id):
        rcode, text_body = s3.get_text(text_id)
        if rcode is return_codes.OK:
            return render_template("text.html", text_body=text_body)
        if rcode is return_codes.S3_KEY_NOT_EXISTS:
            abort(404)
        abort(500)

    from . import auth

    app.register_blueprint(auth.bp)

    return app
