import elasticsearch

from . import utils
from .log import get_logger
from .config.elasticsearch import config

LOGGER = get_logger()

client = None


def init_search_client():
    global client
    if client is None:
        LOGGER.info("Initializing Elasticsearch client")
        client = elasticsearch.AsyncElasticsearch(
            config["host"],
            basic_auth=(config["user"], config["password"]),
            verify_certs=False,
            connections_per_node=config["connections_per_node"],
        )


async def close_search_client():
    if client is not None:
        LOGGER.info("Closing Elasticsearch client")
        await client.close()


class BadRequestError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


async def search(query, from_=0, size=config["page_size"]):
    try:
        response = await client.search(
            index=config["index_name"],
            source=["title"],
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
    return [parse_result_item(item) for item in response["hits"]["hits"]]


def parse_result_item(item):
    return {
        "text_id": item["_id"],
        "text_title": item["_source"]["title"],
        "text_body_highlights": [
            utils.remove_html_tags_except_em(text)
            for text in item["highlight"].get("body", [])
        ],
    }


def log_search_results(query, response):
    metadata = {key: response[key] for key in ("took", "timed_out", "_shards")}
    metadata.update(
        {
            "hits.total": response["hits"]["total"],
            "hits.max_score": response["hits"]["max_score"],
        }
    )
    LOGGER.info(f"Search query '{query}', metadata: {metadata}")
