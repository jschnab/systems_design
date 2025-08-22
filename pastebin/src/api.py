import re
import uuid
from datetime import datetime, timedelta

from . import cache
from . import database
from . import object_store
from .config import config
from .log import get_logger

LOGGER = get_logger()

H1_REGEX = re.compile(r"<h1.*>(.+)</h1>")
SENTENCE_REGEX = re.compile(r"[\w,'&]+( [\w,'&]+)+")
HTML_TAG_REGEX = re.compile(r"<.*?>")
MINIMUM_TITLE_LENGTH = 40
MAXIMUM_TITLE_LENGTH = 60

TTL_TO_HOURS = {
    "1h": 1,
    "1d": 24,
    "1w": 24 * 7,
    "1m": 24 * 30,
    "1y": 24 * 365,
}


def remove_html_tags(text):
    return re.sub(HTML_TAG_REGEX, "", text)


def truncate_title(title):
    result = []
    count = 0
    for word in title.split():
        count += len(word)
        if count > MAXIMUM_TITLE_LENGTH:
            break
        result.append(word)
    return " ".join(result)


def get_text_title(text_body):
    if (match := H1_REGEX.search(text_body)) is not None:
        title = remove_html_tags(match.group(1))
        if title != "":
            return truncate_title(title)
    for match in SENTENCE_REGEX.finditer(text_body):
        if len(match.group(0)) >= MINIMUM_TITLE_LENGTH:
            title = remove_html_tags(match.group(0))
            return truncate_title(title)
    return "Untitled"


async def put_text(
    text_body,
    text_title,
    user_id,
    user_ip,
    ttl,
    burn_after_reading,
    visibility,
):
    creation_timestamp = datetime.now()
    ttl_hours = TTL_TO_HOURS[ttl]
    expiration_timestamp = creation_timestamp + timedelta(hours=ttl_hours)
    text_id = str(uuid.uuid4())
    await object_store.put_text(text_id=text_id, text_body=text_body)
    text_title = text_title or get_text_title(text_body)
    await database.put_text_metadata(
        text_id=text_id,
        text_title=text_title,
        user_id=user_id,
        user_ip=user_ip,
        creation_timestamp=creation_timestamp,
        expiration_timestamp=expiration_timestamp,
        burn_after_reading=burn_after_reading,
        visibility=visibility,
    )
    return text_id


async def get_text(text_id, user):
    metadata = await database.get_text_metadata(text_id)

    if not database.text_is_visible(metadata):
        LOGGER.info(f"Text {text_id} will be deleted, ignoring")
        return

    if database.text_is_private(metadata):
        LOGGER.info(f"Text {text_id} is private")
        if not database.text_owner_matches_logged_user(user, metadata):
            LOGGER.info(f"Text {text_id} accessed by non-owner, ignoring")
            return
        LOGGER.info(f"Text {text_id} accessed by owner")

    text_body = await cache.get(text_id)
    if text_body is not None:
        LOGGER.info(f"Text {text_id} found in cache")
        return text_body
    LOGGER.info(f"Text {text_id} not found in cache")
    text_body = await object_store.get_text(text_id)

    if database.is_text_burn_after_reading(metadata):
        LOGGER.info(f"Text {text_id} should be burned")
        await database.mark_text_for_deletion(text_id)
    else:
        LOGGER.info(f"Text {text_id} should not be burned")
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


async def get_text_owner(text_id):
    return await database.get_text_owner(text_id)


async def get_texts_by_owner(user_id):
    return await database.get_texts_by_owner(user_id)
