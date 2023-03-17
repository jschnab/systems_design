import uuid

from flask import url_for

from . import database
from . import image
from . import object_store
from . import return_codes
from .config import CONFIG


def create_user(user_id, first_name, last_name, password, avatar_id):
    rcode = database.create_user(
        user_id,
        first_name,
        last_name,
        password,
        avatar_id,
    )
    if rcode == return_codes.USER_EXISTS:
        return rcode
    database.create_album(CONFIG["general"]["default_album_name"], user_id)
    return rcode


def put_image(
    image_data,
    image_description,
    user_id,
    tags,
    album_name,
):
    img, thumbnail = image.process_image(image_data)
    image_id = uuid.uuid4()
    object_store.put_image(f"{image_id}", img)
    object_store.put_image(f"{image_id}.thumbnail", thumbnail)
    database.add_image(
        image_id=image_id,
        image_description=image_description,
        owner_id=user_id,
        tags=set(tags),
        album_name=album_name,
    )
    return image_id


def delete_image(image_id, album_name, owner_id, publication_timestamp):
    database.delete_image(
        image_id,
        album_name,
        owner_id,
        publication_timestamp,
    )
    object_store.delete_image(f"{image_id}")
    object_store.delete_image(f"{image_id}.thumbnail")


def put_avatar_image(image_data):
    img, thumbnail = image.process_image(image_data, crop=True)
    image_id = uuid.uuid4()
    object_store.put_image(f"{image_id}", img)
    object_store.put_image(f"{image_id}.thumbnail", thumbnail)
    return image_id


def get_avatar_url(avatar_id):
    if avatar_id is None:
        return url_for("avatar_default")
    return object_store.get_image_url(f"{avatar_id}.thumbnail")


def get_followed_users(user_id):
    ids = database.get_followed_users(user_id)
    followed_users = []
    for i in ids:
        user_info = database.get_user_info(i)
        followed_users.append(
            {
                "id": i,
                "avatar": get_avatar_url(user_info["avatar_id"]),
            }
        )
    return sorted(followed_users, key=lambda x: x["id"])


def get_follower_users(user_id):
    ids = database.get_follower_users(user_id)
    follower_users = []
    for i in ids:
        user_info = database.get_user_info(i)
        follower_users.append(
            {
                "id": i,
                "avatar": get_avatar_url(user_info["avatar_id"]),
            }
        )
    return sorted(follower_users, key=lambda x: x["id"])
