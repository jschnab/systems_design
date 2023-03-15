import uuid

from . import database
from . import image
from . import object_store
from . import return_codes
from .config import CONFIG


def create_user(user_id, first_name, last_name, password):
    rcode = database.create_user(user_id, first_name, last_name, password)
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
