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
    print(f"caching '{key}'")
    CACHE_CLIENT.set(key, value)


def get(key):
    print(f"uncaching '{key}'")
    value = CACHE_CLIENT.get(key)
    if value is not None:
        print("cache hit")
    else:
        print("cache miss")
    return value


def delete(key):
    print(f"evict '{key}'")
    return CACHE_CLIENT.delete(key)
