import os
import secrets
import sys
from datetime import datetime, timedelta

from flask import (
    abort,
    flash,
    Flask,
    render_template,
    request,
    send_from_directory,
    session,
)
from werkzeug.middleware.proxy_fix import ProxyFix

from . import api
from . import auth
from . import database
from .config import config

APP_URL = f"{config['app']['host']}:{config['app']['port']}"
DEFAULT_USER = config["app"]["default_user"]
TEXT_MAX_SIZE = 512000 + sys.getsizeof("")
TEXTS_QUOTA_ANONYMOUS = config["app"]["texts_quota_anonymous"]
TEXTS_QUOTA_USER = config["app"]["texts_quota_user"]
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
        if request.method == "GET":
            return render_template("index.html", msg=None)

        if sys.getsizeof(request.form["text-body"]) > TEXT_MAX_SIZE:
            return render_template("index.html", msg="Text is too large")

        user_id = session.get("user_id", DEFAULT_USER)
        ttl = TTL_TO_HOURS[request.form["ttl"]]
        creation_timestamp = datetime.now()
        expiration_timestamp = creation_timestamp + timedelta(hours=ttl)

        user_ip = request.environ.get(
            "HTTP_X_REAL_IP", request.remote_addr
        )
        count_texts = database.count_recent_texts_by_user(
            user_id=user_id, user_ip=user_ip,
        )

        if user_id == DEFAULT_USER:
            quota = TEXTS_QUOTA_ANONYMOUS
        else:
            quota = TEXTS_QUOTA_USER

        if count_texts >= quota:
            msg = (
                f"User '{user_id}' stored more than {quota} texts during the "
                "past day, come back later"
            )
        else:
            text_id = api.put_text(
                text_body=request.form["text-body"],
                user_id=user_id,
                user_ip=user_ip,
                creation_timestamp=creation_timestamp,
                expiration_timestamp=expiration_timestamp,
            )
            msg = f"Stored text at {APP_URL}/text/{text_id}"

        return render_template("index.html", message=msg)

    @app.route("/text/<text_id>")
    def get_text(text_id):
        text_body = api.get_text(text_id)
        if text_body is None:
            abort(404)
        return render_template("text.html", text_body=text_body)

    @app.route("/delete-text", methods=("POST",))
    def delete_text():
        if request.method == "POST":
            text_id = request.form["text-id"]
            api.delete_text(text_id=text_id, deletion_timestamp=datetime.now())
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

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    app.register_blueprint(auth.bp)

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1,
    )

    return app
