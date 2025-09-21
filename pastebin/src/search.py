import logging
from typing import Optional

import elasticsearch
from elastic_transport import ObjectApiResponse

from . import utils
from .log import get_logger
from .config.elasticsearch import config

LOGGER: logging.Logger = get_logger()

client: Optional[elasticsearch.AsyncElasticsearch] = None


def init_search_client() -> None:
    global client
    if client is None:
        LOGGER.info("Initializing Elasticsearch client")
        client = elasticsearch.AsyncElasticsearch(
            config["host"],
            basic_auth=(config["user"], config["password"]),
            verify_certs=False,
            connections_per_node=config["connections_per_node"],
        )


async def close_search_client() -> None:
    if client is not None:
        LOGGER.info("Closing Elasticsearch client")
        await client.close()


class BadRequestError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


async def search(
    query: str,
    from_: int = 0,
    size: int = config["page_size"],
) -> tuple[list[dict], Optional[int], Optional[int]]:
    if client is None:
        raise RuntimeError("Elasticsearch client is not initialized")
    try:
        response: ObjectApiResponse = await client.search(
            index=config["index_name"],
            # A list of string would work but a dictionary is required to
            # satisfy type hints.
            source={"include": ["title"]},
            q=query,
            from_=from_,
            size=size,
            highlight={"fields": {"title": {}, "body": {}}},
        )
    except elasticsearch.BadRequestError as err:
        message = err.info["error"]["root_cause"][0]["reason"]
        LOGGER.error(f"Bad request: {message}. Query: {query}")
        raise BadRequestError(message)
    except Exception as err:
        LOGGER.error(f"{err.__class__.__name__} {str(err)}. Query: {query}")
        raise

    log_search_results(query, response)

    if from_ > 0:
        previous_offset = max(0, from_ - size)
    else:
        previous_offset = None

    if from_ + size < response["hits"]["total"]["value"]:
        next_offset = from_ + size
    else:
        next_offset = None

    return (
        [parse_result_item(item) for item in response["hits"]["hits"]],
        previous_offset,
        next_offset,
    )


def parse_result_item(item: dict) -> dict:
    return {
        "text_id": item["_id"],
        "text_title": item["_source"]["title"],
        "text_body_highlights": [
            utils.remove_html_tags_except_em(text)
            for text in item["highlight"].get("body", [])
        ],
    }


def log_search_results(query: str, response: ObjectApiResponse) -> None:
    metadata: dict = {
        key: response[key] for key in ("took", "timed_out", "_shards")
    }
    metadata.update(
        {
            "hits.total": response["hits"]["total"],
            "hits.max_score": response["hits"]["max_score"],
        }
    )
    LOGGER.info(f"Search query '{query}', metadata: {metadata}")
