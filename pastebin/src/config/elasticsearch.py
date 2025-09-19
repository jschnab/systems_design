import os

from . import validation


def get_elasticsearch_config():
    return {
        "index_name": os.getenv("MYPASTEBIN_ELASTICSEARCH_TEXTS_INDEX_NAME"),
        "host": os.getenv(
            "MYPASTEBIN_ELASTICSEARCH_HOST", "https://localhost:9200"
        ),
        "user": os.getenv("MYPASTEBIN_ELASTICSEARCH_USER"),
        "password": os.getenv("MYPASTEBIN_ELASTICSEARCH_PASSWORD"),
    }


config = get_elasticsearch_config()
validation.check_config(config)
