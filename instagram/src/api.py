import uuid
from base64 import b64encode

from . import database
from . import image
from . import object_store


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
    image_info = database.get_image_info(uuid.UUID(image_id))
    image_info["data"] = b64encode(
        object_store.get_image(str(image_info["image_id"]))
    ).decode()
    return image_info


def get_user_images(user_id):
    images = database.get_images_by_user(user_id)
    for img in images:
        img["thumbnail"] = b64encode(
            object_store.get_image(f"{img['image_id']}.thumbnail")
        ).decode()
    return images
