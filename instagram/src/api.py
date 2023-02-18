import uuid

from . import database
from . import disk_cache
from . import image
from . import object_store

DISK_CACHE = disk_cache.DiskCache()


def cache_image(image_id):
    path = DISK_CACHE.get_path(image_id)
    if path is None:
        print("api.cache_image() cache miss for", image_id)
        data = object_store.get_image(image_id)
        path = DISK_CACHE.set(image_id, data)
    else:
        print("api.cache_image() cache hit for", image_id)
    return path


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


def get_image(image_id):
    cache_image(image_id)
    return database.get_image_info(uuid.UUID(image_id))


def get_user_images(user_id):
    images = database.get_images_by_user(user_id)
    for img in images:
        thumbnail = f"{img['image_id']}.thumbnail"
        cache_image(thumbnail)
        img["thumbnail"] = thumbnail
    return images


def get_album_info(album_name, user_id):
    # TODO: Create a table that allows querying full image info by album name.
    # Adding album_name to the clustering key of table images_by_user may do
    # the job.
    album_info = database.get_album_info(album_name, user_id)
    album_info["images"] = []
    if album_info["image_ids"] is not None:
        for img_id in album_info["image_ids"]:
            img_info = database.get_image_info(img_id)
            thumbnail = f"{img_id}.thumbnail"
            cache_image(thumbnail)
            img_info["thumbnail"] = thumbnail
            album_info["images"].append(img_info)
    return album_info
