import os
import secrets
import sys
from base64 import b64encode
from datetime import datetime

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
from . import object_store
from .auth import login_required
from .config import CONFIG


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = secrets.token_hex()

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/put-image", methods=("GET", "POST"))
    @login_required
    def put_image():
        message = None
        if request.method == "POST":
            user_id = session.get("user_id")
            tags = request.form["tags"].strip().split()
            image_id = api.put_image(
                image_data=request.files["image"].read(),
                image_description=request.form["image-description"],
                user_id=user_id,
                tags=tags,
                album_name=None,
            )
            message = f"Image saved to {image_id}"

        return render_template("put_image.html", msg=message)

    @app.route("/images/<image_id>")
    def get_image(image_id):
        image_info = api.get_image(image_id)
        if image_info is None:
            abort(404)
        return render_template(
            "image.html",
            image_id=image_id,
            image_description=image_info["description"],
            publication_timestamp=image_info["publication_timestamp"],
            tags=", ".join(image_info["tags"]),
            image_data=image_info["data"],
        )

    @app.route("/user-images/<user_id>")
    def user_images(user_id):
        images = api.get_user_images(user_id)
        return render_template("user_images.html", images=images)

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
