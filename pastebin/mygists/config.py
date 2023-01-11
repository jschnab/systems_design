import os


def get_config():
    # Should be a dictionary where keys are strings and values are dictionaries
    # or scalar values (string, integer).
    return {
        "text_storage": {
            "s3_bucket": os.getenv("MYPASTEBIN_S3_BUCKET"),
            "encoding": os.getenv("MYPASTEBIN_TEXT_ENCODING", "utf-8"),
        },
        "alias_service": {
            "db_host": os.getenv("ALIAS_DB_HOST", "localhost"),
            "db_port": os.getenv("ALIAS_DB_PORT", 5432),
            "db_database": os.getenv("ALIAS_DB_DATABASE"),
            "db_user": os.getenv("ALIAS_DB_USER"),
            "db_password": os.getenv("ALIAS_DB_PASSWORD"),
            "host": os.getenv("ALIAS_SERVICE_HOST", "localhost"),
            "port": os.getenv("ALIAS_SERVICE_PORT", 8000),
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
