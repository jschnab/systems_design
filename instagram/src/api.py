import uuid

from . import database
from . import disk_cache
from . import image
from . import object_store
from . import return_codes
from .config import CONFIG

DISK_CACHE = disk_cache.DiskCache()


def cache_image(image_id):
    path = DISK_CACHE.get_path(image_id)
    if path is None:
        data = object_store.get_image(image_id)
        path = DISK_CACHE.set(image_id, data)
    return path


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
