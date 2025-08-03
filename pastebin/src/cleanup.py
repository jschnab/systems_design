import asyncio
from datetime import datetime

from . import cache
from . import database
from . import object_store
from .log import get_logger

LOGGER = get_logger()


async def cleanup():
    rows = await database.get_texts_for_deletion()
    LOGGER.info(f"Number of texts to cleanup: {len(rows)}")
    for idx, row in enumerate(rows, start=1):
        prefix = f"{idx}/{len(rows)}"
        text_id = row["text_id"]
        LOGGER.info(f"{prefix} Cleaning up: {text_id}")
        LOGGER.info(f"{prefix} Deleting from object store")
        await object_store.delete_text(text_id)
        LOGGER.info(f"{prefix} Deleting from cache")
        await cache.delete(text_id)
        LOGGER.info(f"{prefix} Marking as deleted")
        await database.mark_text_deleted(
            text_id=text_id, deletion_timestamp=datetime.now()
        )
        LOGGER.info(f"{prefix} Finished cleaning up: {text_id}")
    LOGGER.info(f"Finished cleaning up {len(rows)} texts")


async def main():
    cache.init_connection_pool()
    database.init_thread_pool()
    database.init_connection_pool()

    try:
        await cleanup()
    finally:
        await cache.close_connection_pool()
        database.close_thread_pool()
        database.close_connection_pool()


if __name__ == "__main__":
    asyncio.run(main())
