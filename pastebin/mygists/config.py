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
            "port": os.getenv("MYPASTEBIN_DB_PORT", 5432),
            "database": os.getenv("MYPASTEBIN_DB_DATABASE"),
            "user": os.getenv("MYPASTEBIN_DB_USER"),
            "password": os.getenv("MYPASTEBIN_DB_PASSWORD"),
        },
        "app": {
            "host": os.getenv("MYPASTEBIN_HOST", "localhost"),
            "port": os.getenv("MYPASTEBIN_PORT", 5000),
            "default_user": os.getenv("MYPASTEBIN_DEFAULT_USER", "anonymous"),
        }
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
                if v is None:
                    null_values.append(f"{parent}.{k}")
    if null_values != []:
        raise ValueError(
            f"The following values should not be None: "
            f"{', '.join(null_values)}"
        )


config = get_config()
check_config(config)
