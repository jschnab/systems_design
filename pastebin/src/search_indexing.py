"""
This module defines an application that indexes shared texts in the search
engine.

Text events are retrieved from a Kafka topic, then the corresponding text is
retrieved from object storage, and finally the appropriate action is taken
based on the specific event (create or delete).
"""

import asyncio
import enum
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, Any

from confluent_kafka import Consumer, Message

from . import constants as cst
from . import kafka
from . import object_store
from . import search
from .config.debezium import config as debezium_config
from .log import get_logger

LOGGER: logging.Logger = get_logger()

thread_pool = None


def init_thread_pool() -> None:
    """
    Initializes a global thread pool.

    Returns:
        None
    """
    global thread_pool
    if thread_pool is None:
        LOGGER.info("Creating thread pool")
        thread_pool = ThreadPoolExecutor()


def close_thread_pool() -> None:
    """
    Closes the previously initialized global thread pool.

    Returns:
        None
    """
    if thread_pool is not None:
        LOGGER.info("Closing thread pool")
        thread_pool.shutdown()


async def execute_in_thread_pool(function: Callable, args: tuple) -> Any:
    """
    Executes a function or method in a thread pool, to avoid blocking the
    asyncio event loop.

    Args:
        function (Callable): Function or method to execute.
        args (tuple): Tuple of arguments to be passed to `function`.

    Returns:
        Any: Return value of `function` when called with `args`.
    """
    return await asyncio.get_running_loop().run_in_executor(
        thread_pool, partial(function, *args)
    )


class IndexingAction(enum.Enum):
    DELETE = "delete"
    CREATE = "create"


async def parse_kafka_messages(messages: list[Message]) -> list[dict]:
    """
    Parses Kafka messages following the Debezium CDC format and returns a list
    of Elasticsearch bulk indexing operations that can be passed directly to
    the `_bulk` endpoint
    (https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk).

    Kafka messages do not contain the text body, which is fetched from the
    object store.

    Args:
        messages (list[Message]): Kafka messages.

    Returns:
        list[dict]: Bulk indexing operations.
    """
    documents = []
    for msg in messages:
        msg_value = msg.value()
        if msg_value is None:
            LOGGER.warning(
                f"Kafka message value is None. Topic: {msg.topic()}. "
                f"Partition: {msg.partition()}. Offset: {msg.offset()}. "
            )
            continue
        after: dict = json.loads(msg_value.decode())["after"]
        if after["visibility"] != cst.TextVisibility.PUBLIC.value:
            continue
        action: IndexingAction = get_document_indexing_action(after)
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


def get_document_indexing_action(record: dict) -> IndexingAction:
    """
    Extracts the indexing action to perform from Debezium records, either
    create or delete.

    Args:
        record (dict): Debezium record.

    Returns:
        IndexingAction: Action to perform during indexing.
    """
    if any(
        [
            record["to_be_deleted"] == 1,
            record["deletion"] is not None,
        ]
    ):
        return IndexingAction.DELETE
    return IndexingAction.CREATE


async def run_indexing(kafka_consumer: Consumer) -> None:
    """
    Consumes Debezium records from Kafka corresponding to shared texts,
    then indexes them to the search engine in bulk.

    Args:
        kafka_consumer (Consumer): Kafka consumer.

    Returns:
        None
    """
    while True:
        messages: list[Message] = await execute_in_thread_pool(
            kafka.get_message_batch, (kafka_consumer,)
        )
        if not messages:
            continue
        LOGGER.info(f"Fetched {len(messages)} Kafka messages")
        operations: list[dict] = await parse_kafka_messages(messages)
        await search.bulk_index_texts(operations=operations)
        await execute_in_thread_pool(
            kafka.acknowledge_messages, (kafka_consumer, messages)
        )
        LOGGER.info("Acknowledged Kafka messages consumption")


async def main() -> None:
    """
    Initializes search engine and Kafka clients, then runs text indexing.

    Returns:
        None
    """
    LOGGER.info("Initializing search and Kafka clients")
    search.init_search_client()
    kafka_consumer: Consumer = kafka.init_consumer(
        debezium_config["texts_topic"]
    )

    LOGGER.info("Starting search indexing")
    try:
        await run_indexing(kafka_consumer)
    finally:
        LOGGER.info("Closing search client")
        await search.close_search_client()
        LOGGER.info("Closing Kafka consumer")
        kafka_consumer.close()


if __name__ == "__main__":
    asyncio.run(main())
