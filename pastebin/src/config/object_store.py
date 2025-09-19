import os

from . import validation


def get_object_store_config():
    return {
        "bucket": os.getenv("MYPASTEBIN_OBJECT_STORE_BUCKET"),
        "encoding": os.getenv("MYPASTEBIN_TEXT_ENCODING", "utf-8"),
        "endpoint": os.getenv("MYPASTEBIN_OBJECT_STORE_ENDPOINT"),
        "user": os.getenv("MINIO_USER"),
        "password": os.getenv("MINIO_PASSWORD"),
    }


config = get_object_store_config()
validation.check_config(config)
