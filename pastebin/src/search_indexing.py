import asyncio
import enum
import json

from elasticsearch import Elasticsearch

from . import constants as cst
from . import kafka
from . import object_store
from .config.elasticsearch import config as es_config
from .config.debezium import config as debezium_config
from .log import get_logger

LOGGER = get_logger()


class IndexingAction(enum.Enum):
    DELETE = "delete"
    CREATE = "create"


async def parse_kafka_messages(messages):
    documents = []
    for msg in messages:
        after = json.loads(msg.value().decode())["after"]
        if after["visibility"] != cst.TextVisibility.PUBLIC.value:
            continue
        action = get_document_indexing_action(after)
        if action == IndexingAction.DELETE:
            documents.append({"delete": {"_id": after["text_id"]}})
        else:
            documents.append({"index": {"_id": after["text_id"]}})
            documents.append(
                {
                    "title": after["text_title"],
                    "body": await object_store.get_text(after["text_id"]),
                    "created_at": after["creation"],
                }
            )
    return documents


def get_document_indexing_action(record):
    if any(
        [
            record["to_be_deleted"] == 1,
            record["deletion"] is not None,
        ]
    ):
        return IndexingAction.DELETE
    return IndexingAction.CREATE


async def run_indexing(es_client, kafka_consumer):
    while True:
        messages = kafka.get_message_batch(kafka_consumer)
        if not messages:
            continue
        LOGGER.info(f"Fetched {len(messages)} Kafka messages")
        operations = await parse_kafka_messages(messages)
        resp = es_client.bulk(
            index=es_config["index_name"], operations=operations
        )
        LOGGER.info(f"Indexing response: {resp}")
        kafka.acknowledge_messages(kafka_consumer, messages)
        LOGGER.info("Acknowledged Kafka messages consumption")


async def main():
    LOGGER.info("Starting search indexing")

    es_client = Elasticsearch(
        es_config["host"],
        basic_auth=(es_config["user"], es_config["password"]),
        verify_certs=False,
    )
    kafka_consumer = kafka.init_consumer(debezium_config["texts_topic"])

    try:
        await run_indexing(es_client, kafka_consumer)
    finally:
        LOGGER.info("Closing Elasticsearch client")
        es_client.close()
        LOGGER.info("Closing Kafka consumer")
        kafka_consumer.close()


if __name__ == "__main__":
    asyncio.run(main())
