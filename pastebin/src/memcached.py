import functools

from pymemcache.client.base import Client

from .config import config

CACHE_CLIENT = Client(
    config["cache"]["host"],
    encoding=config["cache"]["encoding"],
)


def manage_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"{e.__class__.__name__} when calling '{func}': {e}")
    return wrapper


@manage_exceptions
def put(key, value):
    CACHE_CLIENT.set(key, value)


@manage_exceptions
def get(key):
    value = CACHE_CLIENT.get(key)
    if value is not None:
        return value.decode(config["cache"]["encoding"])


@manage_exceptions
def delete(key):
    return CACHE_CLIENT.delete(key)
