import logging
import logging.config
import os

import yaml

from .config import CONFIG

if "config_path" in CONFIG["logging"]:
    config_path = CONFIG["logging"]["config_path"]
else:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "log_conf.yml"
    )
with open(config_path) as fi:
    config = yaml.load(fi, Loader=yaml.SafeLoader)
    logging.config.dictConfig(config)

BASE_LOGGER = logging.getLogger("base")
