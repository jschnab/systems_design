import os

from . import validation


def get_cache_config() -> dict:
    """
    Builds cache configuration.

    Returns:
        dict: Configuration.
    """
    return {
        "host": os.getenv("MYPASTEBIN_CACHE_HOST", "localhost"),
        "port": int(os.getenv("MYPASTEBIN_CACHE_PORT", 6379)),
        "username": os.getenv("MYPASTEBIN_CACHE_USER"),
        "password": os.getenv("MYPASTEBIN_CACHE_PASSWORD"),
        "encoding": os.getenv("MYPASTEBIN_CACHE_ENCODING", "utf-8"),
        "pool_size": int(os.getenv("MYPASTEBIN_CACHE_CON_POOL_SIZE", 200)),
        "key_prefix": os.getenv("MYPASTEBIN_CACHE_KEY_PREFIX", "pastebin:"),
    }


config: dict = get_cache_config()
validation.check_config(config)
