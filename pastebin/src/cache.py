import functools

import redis

from .config import config

CACHE_CLIENT = redis.Redis(
    host=config["cache"]["host"],
    port=config["cache"]["port"],
    password=config["cache"]["password"],
    encoding=config["cache"]["encoding"],
    decode_responses=True,
)


def manage_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.exceptions.RedisError as e:
            print(
                f"{e.__class__.__name__} when calling "
                f"'{func.__module__}.{func.__name__}': {e}"
            )
    return wrapper


@manage_errors
def put(key, value):
    CACHE_CLIENT.set(key, value)


@manage_errors
def get(key):
    return CACHE_CLIENT.get(key)


@manage_errors
def delete(key):
    return CACHE_CLIENT.delete(key)
