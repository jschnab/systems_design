import configparser
import os


def configure():
    config_path = os.getenv("MYINSTAGRAM_CONFIG_PATH")
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config.ini"
        )
    conf = configparser.ConfigParser()
    conf.read(config_path)
    return conf


CONFIG = configure()
