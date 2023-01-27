import uuid
from datetime import datetime, timedelta

from . import cache
from . import database
from . import object_store

CACHE_TEXT_KEY = "text:{text_id}"
TTL_TO_HOURS = {
    "1h": 1,
    "1d": 24,
    "1w": 24 * 7,
    "1m": 24 * 30,
    "1y": 24 * 365,
}


def put_text(text_body, user_id, user_ip, ttl):
    creation_timestamp = datetime.now()
    ttl_hours = TTL_TO_HOURS[ttl]
    expiration_timestamp = creation_timestamp + timedelta(hours=ttl_hours)
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
    # Mark for deletion in metadata database before deleting from object
    # storage to avoid errors when text ID shows up in web app but then is not
    # found.
    database.mark_text_for_deletion(text_id)
    object_store.delete_text(text_id)
    database.mark_text_deleted(text_id, deletion_timestamp)
    cache.delete(CACHE_TEXT_KEY.format(text_id=text_id))
