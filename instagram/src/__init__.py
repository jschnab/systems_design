import os
import secrets
import uuid
from datetime import datetime, timedelta

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
from . import object_store
from . import return_codes
from .auth import login_required
from .config import CONFIG
from .logging import BASE_LOGGER

# 'Return success' code for Flask views.
OK = "OK"


def format_timestamp(ts):
    return ts.strftime("%a %b %d %Y %H:%M:%S")


def create_app(test_config=None):
    BASE_LOGGER.info("Creating Flask app")
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = secrets.token_hex()

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    @app.route("/")
    @login_required
    def index():
        feed = database.get_user_feed(session["user_id"])
        return render_template("index.html", image_feed=feed)

    @app.route("/put-image", methods=("GET", "POST"))
    @login_required
    def put_image():
        message = None
        user_id = session.get("user_id")
        user_albums = database.get_albums_by_user(user_id)

        if request.method == "POST":
            count_images = database.count_user_images_by_album_timestamp(
                user_id, tuple(user_albums), datetime.now() - timedelta(days=1)
            )
            quota = CONFIG["general"].getint("user_image_quota")
            if count_images > quota:
                message = (
                    f"You reached your image upload quota ({quota} per day)"
                )

            else:
                tags = request.form["tags"].strip().split()
                album_name = request.form["album-name"]
                api.put_image(
                    image_data=request.files["image"].read(),
                    image_description=request.form["image-description"],
                    user_id=user_id,
                    tags=tags,
                    album_name=album_name,
                )
                message = f"Image saved in album '{album_name}'"

        return render_template(
            "put_image.html", message=message, user_albums=user_albums
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

        return render_template("put_album.html", message=message)

    @app.route("/images/<image_id>")
    @login_required
    def get_image(image_id):
        image_id = uuid.UUID(image_id)
        user_id = session["user_id"]
        image_info = database.get_image_info(image_id)

        if image_info["tags"] is None:
            image_info["tags"] = set()

        if image_info is None:
            abort(404)

        if database.get_image_like_by_user(image_id, user_id) is not None:
            user_liked_image = True
        else:
            user_liked_image = False

        comments = database.get_image_comments(image_id)

        return render_template(
            "image.html",
            image_id=str(image_id),
            owner_id=image_info["owner_id"],
            image_description=image_info["description"],
            publication_timestamp=image_info["publication_timestamp"],
            tags=", ".join(image_info["tags"]),
            user_liked_image=user_liked_image,
            comments=comments,
        )

    @app.route("/like-image", methods=("POST",))
    @login_required
    def like_image():
        user_id = session["user_id"]
        image_id = uuid.UUID(request.form["image_id"])
        database.like_image(image_id, user_id)
        database.increment_image_popularity(image_id)
        return OK

    @app.route("/comment-image", methods=("POST",))
    @login_required
    def comment_image():
        image_id = uuid.UUID(request.form["image_id"])
        database.comment_image(
            image_id,
            session["user_id"],
            request.form["comment"],
        )
        database.increment_image_popularity(image_id)
        return OK

    @app.route("/user-images/<user_id>")
    @login_required
    def user_images(user_id):
        images = database.get_images_by_user(user_id)
        return render_template(
            "user_images.html", user_id=user_id, images=images
        )

    @app.route("/user-albums/<user_id>")
    @login_required
    def user_albums(user_id):
        albums = database.get_albums_by_user(user_id)
        return render_template(
            "user_albums.html", user_id=user_id, albums=albums
        )

    @app.route("/albums/<user_id>/<album_name>")
    @login_required
    def album_info(album_name, user_id):
        album_info = database.get_album_info(album_name, user_id)
        images = database.get_album_images(album_name, user_id)
        return render_template(
            "album.html",
            user_id=user_id,
            album_info=album_info,
            images=images,
        )

    @app.route("/follow-user", methods=("GET", "POST"))
    @login_required
    def follow_user():
        msg = None
        if request.method == "POST":
            followed_user_id = request.form["followed-user-id"]
            if not database.user_exists(followed_user_id):
                msg = f"User '{followed_user_id}' does not exist"
            elif followed_user_id == session["user_id"]:
                msg = "You cannot follow yourself"
            else:
                database.follow_user(
                    session["user_id"],
                    followed_user_id,
                )
                msg = f"You now follow user '{followed_user_id}'"
        return render_template("follow_user.html", message=msg)

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

    @app.route("/like_on.png")
    def like_on_icon():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "like_on.png",
            mimetype="image/png",
        )

    @app.route("/like_off.png")
    def like_off_icon():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "like_off.png",
            mimetype="image/png",
        )

    app.register_blueprint(auth.bp)

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1,
    )

    app.jinja_env.filters.update(
        fmt_ts=format_timestamp,
        image_url=object_store.get_image_url,
    )

    BASE_LOGGER.info("Finished creating Flask app")
    return app
