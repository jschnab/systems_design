import functools

import redis.asyncio as redis
from redis.exceptions import RedisError

from .circuit_breaker import AsyncCircuitBreaker
from .config import config
from .log import get_logger

EXPIRATION_DEFAULT = 3600 * 24  # 1 day
KEY_PREFIX = config["cache"]["key_prefix"]
LOGGER = get_logger()

circuit_breaker = AsyncCircuitBreaker(monitored_exceptions=(RedisError,))

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


async def close_connection_pool():
    if connection_pool is not None:
        LOGGER.info("Closing cache connection pool")
        await connection_pool.aclose()


def manage_errors(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        # The cache contains redundant data, so we can simply log errors and
        # move on, data will be retrieved from the object store.
        except Exception as err:
            LOGGER.error(
                f"{err.__class__.__name__} when calling "
                f"'{func.__module__}.{func.__name__}': {err}"
            )

    return wrapper


@manage_errors
@circuit_breaker
async def put(key, value, ex=EXPIRATION_DEFAULT):
    async with redis.Redis(connection_pool=connection_pool) as client:
        await client.set(f"{KEY_PREFIX}{key}", value, ex=ex)


@manage_errors
@circuit_breaker
async def get(key):
    async with redis.Redis(connection_pool=connection_pool) as client:
        return await client.get(f"{KEY_PREFIX}{key}")


@manage_errors
@circuit_breaker
async def delete(key):
    async with redis.Redis(connection_pool=connection_pool) as client:
        return await client.delete(f"{KEY_PREFIX}{key}")
