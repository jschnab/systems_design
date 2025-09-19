import os

from . import validation


def get_kafka_config():
    return {
        "bootstrap_servers": os.getenv(
            "MYPASTEBIN_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        ),
        "group_id": os.getenv(
            "MYPASTEBIN_KAFKA_CONSUMER_GROUP_ID", "search-consumer-1"
        ),
        "auto_offset_reset": os.getenv(
            "MYPASTEBIN_KAFKA_CONSUMER_AUTO_OFFSET_RESET", "earliest"
        ),
        "enable_auto_offset_store": os.getenv(
            "MYPASTEBIN_KAFKA_CONSUMER_ENABLE_AUTO_OFFSET_STORE", False
        ),
        "fetch_min_bytes": os.getenv(
            "MYPASTEBIN_KAFKA_CONSUMER_FETCH_MIN_BYTES", 1000
        ),
        "fetch_max_wait_ms": os.getenv(
            "MYPASTEBIN_KAFKA_CONSUMER_FETCH_MAX_WAIT_MS", 1000
        ),
        "isolation_level": os.getenv(
            "MYPASTEBIN_KAFKA_CONSUMER_ISOLATION_LEVEL", "read_committed"
        ),
        "message_batch_size": os.getenv(
            "MYPASTEBIN_KAFKA_MESSAGE_BATCH_SIZE", 5
        ),
        "poll_timeout": os.getenv(
            "MYPASTEBIN_KAFKA_CONSUMER_POLL_TIMEOUT", 1.0
        ),
    }


config = get_kafka_config()
validation.check_config(config)
