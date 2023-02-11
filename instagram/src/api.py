import uuid

from . import database
from . import image
from . import object_store


def publish_image(
    image_data,
    image_title,
    user_id,
    tags,
    album_id,
    filter_name,
):
    img, thumbnail = image.process_image(image_data)
    image_id = uuid.uuid4()
    object_store.put_image(f"{image_id}", img)
    object_store.put_image(f"{image_id}.thumbnail", thumbnail)
    database.put_image_metadata(
        image_id=image_id,
        image_title=image_title,
        owner_id=user_id,
        tags=set(tags),
        album_id=album_id,
        filter_name=filter_name,
    )


def delete_image(image_id):
    """
    Delete an image from the object store and mark it as deleted in metadata.

    :param uuid.UUID image_id: Image identifier.
    :returns: None.
    """
    database.mark_image_deleted(image_id)
    object_store.delete_image(f"{image_id}")
    object_store.delete_image(f"{image_id}.thumbnail")
