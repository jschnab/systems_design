import os

from . import validation


def get_database_config():
    return {
        "host": os.getenv("MYPASTEBIN_DB_HOST", "localhost"),
        "port": int(os.getenv("MYPASTEBIN_DB_PORT", 3306)),
        "database": os.getenv("MYPASTEBIN_DB_DATABASE"),
        "user": os.getenv("MYPASTEBIN_DB_USER"),
        "password": os.getenv("MYPASTEBIN_DB_PASSWORD"),
        "pool_size": int(os.getenv("MYPASTEBIN_DB_CON_POOL_SIZE", 32)),
    }


config = get_database_config()
validation.check_config(config)
