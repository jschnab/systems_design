import os

from . import validation


def get_debezium_config() -> dict:
    """
    Builds Debezium configuration.

    Returns:
        dict: Configuration.
    """
    return {
        "texts_topic": os.getenv("MYPASTEBIN_DEBEZIUM_TEXTS_TOPIC"),
    }


config: dict = get_debezium_config()
validation.check_config(config)
