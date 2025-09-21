import os

from . import validation


def get_elasticsearch_config() -> dict:
    """
    Builds Elasticsearch configuration.

    Returns:
        dict: Configuration.
    """
    return {
        "index_name": os.getenv("MYPASTEBIN_ELASTICSEARCH_TEXTS_INDEX_NAME"),
        "host": os.getenv(
            "MYPASTEBIN_ELASTICSEARCH_HOST", "https://localhost:9200"
        ),
        "user": os.getenv("MYPASTEBIN_ELASTICSEARCH_USER"),
        "password": os.getenv("MYPASTEBIN_ELASTICSEARCH_PASSWORD"),
        "connections_per_node": int(
            os.getenv("MYPASTEBIN_ELASTICSEARCH_CONNECTIONS_PER_NODE", 10)
        ),
        "page_size": int(os.getenv("MYPASTEBIN_ELASTICSEARCH_PAGE_SIZE", 10)),
    }


config: dict = get_elasticsearch_config()
validation.check_config(config)
