import uuid

from . import database
from . import object_store


def store_text(text_body, user_id, creation_timestamp, expiration_timestamp):
    text_id = str(uuid.uuid4())
    object_store.put_text(key=text_id, text_body=text_body)
    database.put_text_metadata(
        text_id=text_id,
        user_id=user_id,
        creation_timestamp=creation_timestamp,
        expiration_timestamp=expiration_timestamp,
    )
    return text_id
