import os

from . import validation


def get_app_config() -> dict:
    """
    Builds general application configuration.

    Returns:
        dict: Configuration
    """
    return {
        "url": os.getenv("MYPASTEBIN_URL", "localhost"),
        "default_user": os.getenv("MYPASTEBIN_DEFAULT_USER", "anonymous"),
        "texts_quota_anonymous": int(
            os.getenv("MYPASTEBIN_TEXTS_QUOTA_ANONYMOUS", 10)
        ),
        "texts_quota_user": int(os.getenv("MYPASTEBIN_TEXTS_QUOTA_USER", 100)),
        "log_level": os.getenv("MYPASTEBIN_LOG_LEVEL", "info"),
    }


config: dict = get_app_config()
validation.check_config(config)
