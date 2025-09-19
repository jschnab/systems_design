import os

from . import validation


def get_cache_config():
    return {
        "host": os.getenv("MYPASTEBIN_CACHE_HOST", "localhost"),
        "port": os.getenv("MYPASTEBIN_CACHE_PORT", 6379),
        "username": os.getenv("MYPASTEBIN_CACHE_USER"),
        "password": os.getenv("MYPASTEBIN_CACHE_PASSWORD"),
        "encoding": os.getenv("MYPASTEBIN_CACHE_ENCODING", "utf-8"),
        "pool_size": os.getenv("MYPASTEBIN_CACHE_CON_POOL_SIZE", 200),
        "key_prefix": os.getenv("MYPASTEBIN_CACHE_KEY_PREFIX", "pastebin:"),
    }


config = get_cache_config()
validation.check_config(config)
