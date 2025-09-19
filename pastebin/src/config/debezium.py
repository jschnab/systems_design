import os

from . import validation


def get_debezium_config():
    return {
        "texts_topic": os.getenv("MYPASTEBIN_DEBEZIUM_TEXTS_TOPIC"),
    }


config = get_debezium_config()
validation.check_config(config)
