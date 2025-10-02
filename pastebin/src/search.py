"""
This module contains utilities to interact with the search engine. The
interface is opaque to the underlying search technology used.
"""

import logging
from datetime import datetime
from typing import Optional

import elasticsearch
from elastic_transport import ObjectApiResponse

from . import utils
from .log import get_logger
from .config.search import config

LOGGER: logging.Logger = get_logger()

client: Optional[elasticsearch.AsyncElasticsearch] = None


def init_search_client() -> None:
    """
    Initializes the search engine client. This function should be run prior to
    any other use of this module.

    Returns:
        None
    """
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
    """
    Closes the search engine client. This function should be run when work
    involving the search engine is done, to avoid leaking resources.

    Returns:
        None
    """
    if client is not None:
        LOGGER.info("Closing Elasticsearch client")
        await client.close()


class BadRequestError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


async def search_texts(
    query: str,
    page_start: int = 0,
    page_size: int = config["page_size"],
) -> tuple[list[dict], Optional[int], Optional[int]]:
    """
    Performs a full text search on texts based on Elasticsearch's query string
    syntax.

    The search is paginated. The result offset when a page should start is
    specified with the parameter `page_start`. Page size is specified with the
    parameter `page_size`.

    Args:
        query (str): Query string.
        page_start (int, optional): Result offset where the page of results
            should start. Defaults to 0.
        page_size (int, optional): Result page size. Defaults to the value
            defined in the configuration.

    Returns:
        tuple: The first element is the list of search results. The second
            element is the result offset of the previous page. The third and
            last element is the result offset of the next page.

    Raises:
        BadRequestError: If the query syntax is not correct.
        Exception: Any other error encountered when running the search query.
    """
    if client is None:
        raise RuntimeError("Elasticsearch client is not initialized")
    try:
        response: ObjectApiResponse = await client.search(
            index=config["index_name"],
            # A list of string would work but a dictionary is required to
            # satisfy type hints.
            source={"include": ["title", "created_at"]},
            q=query,
            from_=page_start,
            size=page_size,
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

    if page_start > 0:
        previous_offset = max(0, page_start - page_size)
    else:
        previous_offset = None

    if page_start + page_size < response["hits"]["total"]["value"]:
        next_offset = page_start + page_size
    else:
        next_offset = None

    return (
        [parse_result_item(item) for item in response["hits"]["hits"]],
        previous_offset,
        next_offset,
    )


def parse_result_item(item: dict) -> dict:
    """
    Parses search results and returns them in a format agnostic to the format
    of Elasticsearch hits.

    Args:
        item (dict): A dictionary containing a single Elasticsearch result hit.

    Returns:
        dict: Text identifier, title, and body match highlights.
    """
    return {
        "text_id": item["_id"],
        "text_title": item["_source"]["title"],
        "text_creation_timestamp": format_timestamp(
            item["_source"]["created_at"]
        ),
        "text_body_highlights": [
            utils.remove_html_tags_except_em(text)
            for text in item.get("highlight", {}).get("body", [])
        ],
    }


def format_timestamp(timestamp: str) -> str:
    """
    Reformats at timestamp string given by Elasticsearch to YYYY-MM-DD
    HH:MM:SS.

    Args:
        timestamp (str): Timestamp string as YYYY-MM-DDTHH:MM:SSZ.

    Returns:
        str: Timestamp string as YYYY-MM-DD HH:MM:SS.
    """
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def log_search_results(query: str, response: ObjectApiResponse) -> None:
    """
    Logs Elasticsearch search results metadata, excluding hits.

    Args:
        query (str): Query string.
        response (ObjectApiResponse): Elasticsearch search response.

    Returns:
        None
    """
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


async def bulk_index_texts(operations: list[dict]) -> None:
    """
    Indexes texts in bulk.

    Args:
        operations (list[dict]): List of indexing operations to perform. The
        format should follow the format required by the Elasticsearch `_bulk`
        endpoint
        (https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk).

    Returns:
        None
    """
    if client is None:
        raise RuntimeError("Elasticsearch client is not initialized")
    response: ObjectApiResponse = await client.bulk(
        index=config["index_name"], operations=operations
    )
    LOGGER.info(f"Bulk indexing response: {response}")
