import os
import secrets

from flask import (
    abort,
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
from . import return_codes
from .auth import login_required


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
        user_id = session.get("user_id")
        user_albums = database.get_albums_by_user(user_id)

        if request.method == "POST":
            tags = request.form["tags"].strip().split()
            image_id = api.put_image(
                image_data=request.files["image"].read(),
                image_description=request.form["image-description"],
                user_id=user_id,
                tags=tags,
                album_name=request.form["album-name"],
            )
            message = f"Image saved to {image_id}"

        return render_template(
            "put_image.html", msg=message, user_albums=user_albums
        )

    @app.route("/put-album", methods=("GET", "POST"))
    @login_required
    def put_album():
        message = None
        if request.method == "POST":
            user_id = session.get("user_id")
            album_name = request.form["album-name"]
            rcode = database.create_album(
                album_name=album_name, user_id=user_id
            )
            if rcode == return_codes.ALBUM_EXISTS:
                message = "Album already exists"
            elif rcode == return_codes.OK:
                message = f"Album '{album_name}' successfully created"
            else:
                abort(500)

        return render_template("put_album.html", msg=message)

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
        )

    @app.route("/user-images/<user_id>")
    def user_images(user_id):
        images = api.get_user_images(user_id)
        return render_template("user_images.html", images=images)

    @app.route("/user-albums/<user_id>")
    def user_albums(user_id):
        albums = database.get_albums_by_user(user_id)
        return render_template(
            "user_albums.html", albums=albums, user_id=user_id
        )

    @app.route("/albums/<user_id>/<album_name>")
    def album_info(album_name, user_id):
        album_info = api.get_album_info(album_name, user_id)
        return render_template("album.html", album_info=album_info)

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    @app.route("/folder.png")
    def album_icon():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "folder.png",
            mimetype="image/png",
        )

    @app.route("/static-image/<image_id>")
    def get_static_image(image_id):
        print("__init__.get_static_images() getting static image:", image_id)
        dirname, filename = os.path.split(api.cache_image(image_id))
        return send_from_directory(
            dirname, filename, mimetype="image/*",
        )

    app.register_blueprint(auth.bp)

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1,
    )

    return app
