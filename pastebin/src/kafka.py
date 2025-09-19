from confluent_kafka import Consumer, KafkaException

from .config.kafka import config
from .log import get_logger

LOGGER = get_logger()

CONSUMER_CONFIG = {
    "bootstrap.servers": config["bootstrap_servers"],
    "group.id": config["group_id"],
    "auto.offset.reset": config["auto_offset_reset"],
    "enable.auto.offset.store": config["enable_auto_offset_store"],
    "fetch.min.bytes": config["fetch_min_bytes"],
    "fetch.wait.max.ms": config["fetch_max_wait_ms"],
    "isolation.level": config["isolation_level"],
}

MESSAGE_BATCH_SIZE = config["message_batch_size"]
POLL_TIMEOUT = config["poll_timeout"]


def init_consumer(topic, configuration=CONSUMER_CONFIG):
    consumer = Consumer(configuration)
    consumer.subscribe([topic])
    return consumer


def get_message_batch(
    consumer,
    batch_size=MESSAGE_BATCH_SIZE,
    poll_timeout=POLL_TIMEOUT,
):
    messages = []
    for _ in range(batch_size):
        msg = consumer.poll(POLL_TIMEOUT)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())
        messages.append(msg)
    return messages


def acknowledge_messages(consumer, messages):
    for msg in messages:
        consumer.store_offsets(msg)
