import redis

from .config import config

CACHE_CLIENT = redis.Redis(
    host=config["cache"]["host"],
    port=config["cache"]["port"],
    password=config["cache"]["password"],
    encoding=config["cache"]["encoding"],
    decode_responses=True,
)


def put(key, value):
    CACHE_CLIENT.set(key, value)


def get(key):
    return CACHE_CLIENT.get(key)


def delete(key):
    return CACHE_CLIENT.delete(key)
