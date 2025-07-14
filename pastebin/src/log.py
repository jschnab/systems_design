import logging

from .config import config


def get_logger() -> logging.Logger:
    """
    Configure logging.
    :returns: logger object
    """
    level = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    logging.basicConfig(
        format="%(asctime)s %(name)s %(filename)s %(levelname)s %(message)s",
        level=level[config["app"]["log_level"]],
    )
    return logging.getLogger("pastebin")
