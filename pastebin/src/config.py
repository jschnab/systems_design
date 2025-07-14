import os


def get_config():
    # Should be a dictionary where keys are strings and values are dictionaries
    # or scalar values (string, integer).
    return {
        "text_storage": {
            "s3_bucket": os.getenv("MYPASTEBIN_S3_BUCKET"),
            "encoding": os.getenv("MYPASTEBIN_TEXT_ENCODING", "utf-8"),
        },
        "database": {
            "host": os.getenv("MYPASTEBIN_DB_HOST", "localhost"),
            "port": os.getenv("MYPASTEBIN_DB_PORT"),
            "database": os.getenv("MYPASTEBIN_DB_DATABASE"),
            "user": os.getenv("MYPASTEBIN_DB_USER"),
            "password": os.getenv("MYPASTEBIN_DB_PASSWORD"),
            "pool_size": os.getenv("MYPASTEBIN_DB_CON_POOL_SIZE", 10),
        },
        "app": {
            "url": os.getenv("MYPASTEBIN_URL", "localhost"),
            "default_user": os.getenv("MYPASTEBIN_DEFAULT_USER", "anonymous"),
            "texts_quota_anonymous": os.getenv(
                "MYPASTEBIN_TEXTS_QUOTA_ANONYMOUS", 10
            ),
            "texts_quota_user": os.getenv("MYPASTEBIN_TEXTS_QUOTA_USER", 100),
            "log_level": os.getenv("MYPASTEBIN_LOG_LEVEL", "info"),
        },
        "cache": {
            "host": os.getenv("MYPASTEBIN_CACHE_HOST", "localhost"),
            "port": os.getenv("MYPASTEBIN_CACHE_PORT", 6379),
            "username": os.getenv("MYPASTEBIN_CACHE_USER"),
            "password": os.getenv("MYPASTEBIN_CACHE_PASSWORD"),
            "encoding": os.getenv("MYPASTEBIN_CACHE_ENCODING", "utf-8"),
            "pool_size": os.getenv("MYPASTEBIN_CACHE_CON_POOL_SIZE", 10),
            "key_prefix": os.getenv(
                "MYPASTEBIN_CACHE_KEY_PREFIX",
                "pastebin:"
            ),
        },
    }


def check_config(cnf):
    stack = [(cnf, None)]
    null_values = []
    while stack != []:
        cur, parent = stack.pop()
        for k, v in cur.items():
            if isinstance(v, dict):
                stack.append(
                    (v, f"{parent + '.' if parent is not None else ''}{k}")
                )
            else:
                full_key = f"{parent}.{k}"
                if v is None:
                    null_values.append(full_key)
    if null_values != []:
        raise ValueError(
            f"The following values should not be None: "
            f"{', '.join(null_values)}"
        )


config = get_config()
check_config(config)
