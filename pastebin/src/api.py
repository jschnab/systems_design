import uuid
from datetime import datetime, timedelta

from . import cache
from . import database
from . import object_store
from .config import config
from .log import get_logger

TTL_TO_HOURS = {
    "1h": 1,
    "1d": 24,
    "1w": 24 * 7,
    "1m": 24 * 30,
    "1y": 24 * 365,
}

LOGGER = get_logger()


async def put_text(text_body, user_id, user_ip, ttl):
    creation_timestamp = datetime.now()
    ttl_hours = TTL_TO_HOURS[ttl]
    expiration_timestamp = creation_timestamp + timedelta(hours=ttl_hours)
    text_id = str(uuid.uuid4())
    await object_store.put_text(text_id=text_id, text_body=text_body)
    await database.put_text_metadata(
        text_id=text_id,
        user_id=user_id,
        user_ip=user_ip,
        creation_timestamp=creation_timestamp,
        expiration_timestamp=expiration_timestamp,
    )
    return text_id


async def get_text(text_id):
    text_body = await cache.get(text_id)
    if text_body is not None:
        return text_body
    text_body = await object_store.get_text(text_id)
    if text_body is not None:
        await cache.put(text_id, text_body)
    return text_body


async def delete_text(text_id, deletion_timestamp):
    # Mark for deletion in metadata database before deleting from object
    # storage to avoid errors when text ID shows up in web app but then is not
    # found.
    await database.mark_text_for_deletion(text_id)
    await object_store.delete_text(text_id)
    await database.mark_text_deleted(text_id, deletion_timestamp)
    await cache.delete(text_id)


async def user_exceeded_quota(user_id, user_ip):
    if user_id == config["app"]["default_user"]:
        count_texts = await database.count_recent_texts_by_anonymous_user(
            user_ip
        )
        quota = config["app"]["texts_quota_anonymous"]
    else:
        count_texts = await database.count_recent_texts_by_logged_user(user_id)
        quota = config["app"]["texts_quota_user"]

    return count_texts > quota
