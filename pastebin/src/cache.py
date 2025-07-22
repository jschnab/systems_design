import functools

import redis.asyncio as redis
from redis.exceptions import RedisError

from .config import config
from .log import get_logger

EXPIRATION_DEFAULT = 3600 * 24  # 1 day
KEY_PREFIX = config["cache"]["key_prefix"]
LOGGER = get_logger()

connection_pool = None


def init_connection_pool():
    global connection_pool
    if connection_pool is None:
        LOGGER.info("Creating cache connection pool")
        connection_pool = redis.connection.ConnectionPool(
            max_connections=config["cache"]["pool_size"],
            host=config["cache"]["host"],
            port=config["cache"]["port"],
            username=config["cache"]["username"],
            password=config["cache"]["password"],
            encoding=config["cache"]["encoding"],
            decode_responses=True,
        )


def close_connection_pool():
    if connection_pool is not None:
        LOGGER.info("Closing cache connection pool")
        connection_pool.aclose()


def manage_errors(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except RedisError as e:
            LOGGER.error(
                f"{e.__class__.__name__} when calling "
                f"'{func.__module__}.{func.__name__}': {e}"
            )

    return wrapper


@manage_errors
async def put(key, value, ex=EXPIRATION_DEFAULT):
    async with redis.Redis(connection_pool=connection_pool) as client:
        await client.set(f"{KEY_PREFIX}{key}", value, ex=ex)


@manage_errors
async def get(key):
    async with redis.Redis(connection_pool=connection_pool) as client:
        return await client.get(f"{KEY_PREFIX}{key}")


@manage_errors
async def delete(key):
    async with redis.Redis(connection_pool=connection_pool) as client:
        return await client.delete(f"{KEY_PREFIX}{key}")
