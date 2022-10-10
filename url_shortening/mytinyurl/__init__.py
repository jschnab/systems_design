import os
import secrets
from urllib.parse import quote_plus

import requests
from flask import (
    abort,
    Flask,
    g,
    redirect,
    render_template,
    request,
    session,
)

from . import mongo

APP_URL = "127.0.0.1:5000"
DEFAULT_USER = "anonymous"
TTL_TO_HOURS = {
    "1h": 1,
    "1d": 24,
    "1w": 24 * 7,
    "1m": 24 * 30,
    "1y": 24 * 365,
}

mongo_client = mongo.Client()


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
        user_urls = []

        if request.method == "POST":
            username = session.get("username", DEFAULT_USER)
            long_url = request.form["longurl"]
            alias = request.form["custom-alias"]
            ttl = TTL_TO_HOURS[request.form["ttl"]]

            if alias:
                alias = quote_plus(alias)
                if mongo_client.get_url(alias) is not None:
                    msg = f"Error: alias '{alias}' already exists"
            else:
                alias_host = os.getenv("ALIAS_SERVICE_HOST")
                alias_port = os.getenv("ALIAS_SERVICE_PORT")
                alias = requests.get(
                    f"http://{alias_host}:{alias_port}/get-alias"
                ).json()["alias"]

            if msg is None:
                mongo_client.create_url(alias, long_url, username, ttl)
                msg = f"Created short URL: {APP_URL}/{alias}"

        if g.user:
            user_urls = mongo_client.get_urls_by_user(g.user["_id"])
            for u in user_urls:
                u["alias"] = f"{APP_URL}/{u['_id']}"
                u["created_on"] = u["created_on"].strftime("%m/%d/%Y %H:%M:%S")
                u["ttl"] = u["ttl"].strftime("%m/%d/%Y %H:%M:%S")


        return render_template("index.html", message=msg, myurls=user_urls)

    @app.route("/<alias>")
    def alias(alias):
        original_url = mongo_client.get_url(alias)
        if original_url is None:
            abort(404)
        return redirect(original_url)

    from . import auth
    app.register_blueprint(auth.bp)

    return app
