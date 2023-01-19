import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from requests.packages.urllib3.util.retry import Retry

from .config import config

MAX_RETRIES = 5
BACKOFF_FACTOR = 0.1
RETRY_ON = (500, 502, 503, 504)


def create_session(
    max_retries=MAX_RETRIES,
    backoff_factor=BACKOFF_FACTOR,
    retry_on=RETRY_ON,
):
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        read=max_retries,
        connect=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=retry_on,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


SESSION = create_session()


def get_id():
    id_service_host = config["alias_service"]["host"]
    id_service_port = config["alias_service"]["port"]
    try:
        response = SESSION.get(
            f"http://{id_service_host}:{id_service_port}/get-alias"
        )
        return response.json()["alias"]
    except RequestException:
        pass
