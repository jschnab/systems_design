import uuid

from . import cache
from . import database
from . import object_store

CACHE_TEXT_KEY = "text:{text_id}"


def put_text(
    text_body, user_id, user_ip, creation_timestamp, expiration_timestamp
):
    text_id = str(uuid.uuid4())
    object_store.put_text(text_id=text_id, text_body=text_body)
    database.put_text_metadata(
        text_id=text_id,
        user_id=user_id,
        user_ip=user_ip,
        creation_timestamp=creation_timestamp,
        expiration_timestamp=expiration_timestamp,
    )
    return text_id


def get_text(text_id):
    text_body = cache.get(CACHE_TEXT_KEY.format(text_id=text_id))
    if text_body is not None:
        return text_body
    text_body = object_store.get_text(text_id)
    cache.put(CACHE_TEXT_KEY.format(text_id=text_id), text_body)
    return text_body


def delete_text(text_id, deletion_timestamp):
    database.mark_text_deleted(text_id, deletion_timestamp)
    object_store.delete_text(text_id)
    cache.delete(CACHE_TEXT_KEY.format(text_id=text_id))