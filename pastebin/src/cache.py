import functools

import redis.asyncio as redis

from .config import config
from .log import get_logger

EXPIRATION_DEFAULT = 3600 * 24  # 1 day
KEY_PREFIX = config["cache"]["key_prefix"]

CON_POOL = redis.connection.ConnectionPool(
    max_connections=config["cache"]["pool_size"],
    host=config["cache"]["host"],
    port=config["cache"]["port"],
    # username=config["cache"]["username"],
    # password=config["cache"]["password"],
    encoding=config["cache"]["encoding"],
    decode_responses=True,
)

LOGGER = get_logger()


def manage_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.exceptions.RedisError as e:
            LOGGER.error(
                f"{e.__class__.__name__} when calling "
                f"'{func.__module__}.{func.__name__}': {e}"
            )

    return wrapper


async def put(key, value, ex=EXPIRATION_DEFAULT):
    async with redis.Redis(connection_pool=CON_POOL) as client:
        await client.set(f"{KEY_PREFIX}{key}", value, ex=ex)


async def get(key):
    async with redis.Redis(connection_pool=CON_POOL) as client:
        return await client.get(f"{KEY_PREFIX}{key}")


async def delete(key):
    async with redis.Redis(connection_pool=CON_POOL) as client:
        return await client.delete(f"{KEY_PREFIX}{key}")
