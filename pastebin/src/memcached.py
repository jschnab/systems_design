import functools

from pymemcache.client.base import Client

from .config.cache import config
from .log import get_logger

CACHE_CLIENT = Client(
    config["host"],
    encoding=config["encoding"],
)

LOGGER = get_logger()


def manage_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            LOGGER.error(f"{e.__class__.__name__} when calling '{func}': {e}")

    return wrapper


@manage_exceptions
def put(key, value):
    CACHE_CLIENT.set(key, value)


@manage_exceptions
def get(key):
    value = CACHE_CLIENT.get(key)
    if value is not None:
        return value.decode(config["encoding"])


@manage_exceptions
def delete(key):
    return CACHE_CLIENT.delete(key)
