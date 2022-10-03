import os
import secrets

import requests
from flask import (
    abort,
    flash,
    Flask,
    redirect,
    render_template,
    request,
)

import database


class DB:
    def __init__(self):
        self.con = database.connect()

    def get_url(self, alias):
        if self.con.closed:
            self.con = database.connect()
        return database.get_url(alias, self.con)

    def create_url(self, alias, original, user, ttl):
        if self.con.closed:
            self.con = database.connect()
        database.create_url(
            alias, original, user, self.con, ttl
        )


app = Flask(__name__)
app.secret_key = secrets.token_hex()
db = DB()


@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        long_url = request.form["longurl"]
        alias_host = os.getenv("ALIAS_SERVICE_HOST")
        alias_port = os.getenv("ALIAS_SERVICE_PORT")
        alias = requests.get(
            f"http://{alias_host}:{alias_port}/get-alias"
        ).json()["alias"]
        db.create_url(alias, long_url, "anonymous", 24)
        flash(f"Created alias for {long_url}: http://127.0.0.1:5000/{alias}")

    return render_template("index.html")


@app.route("/<alias>")
def alias(alias):
    original_url = db.get_url(alias)
    if original_url is None:
        abort(404)
    return redirect(original_url)
