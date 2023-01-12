import functools

import psycopg2
import psycopg2.errors
import psycopg2.extensions
import psycopg2.extras

from . import return_codes
from . import sql_queries
from .config import config

DB_CONFIG = {
    "host": config["database"]["host"],
    "port": config["database"]["port"],
    "database": config["database"]["database"],
    "user": config["database"]["user"],
    "password": config["database"]["password"],
}


def manage_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        rcode = return_codes.OK
        retval = None
        try:
            retval = func(*args, **kwargs)
        except psycopg2.errors.UniqueViolation:
            rcode = return_codes.USER_EXISTS
        except psycopg2.Error:
            rcode = return_codes.UNKOWN_ERROR
        return rcode, retval
    return wrapper


@manage_errors
def put_text_metadata(
    text_id,
    user_id,
    creation_timestamp,
    expiration_timestamp,
):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.INSERT_TEXT,
                (
                    text_id,
                    f"{config['text_storage']['s3_bucket']}/{text_id}",
                    user_id,
                    creation_timestamp,
                    expiration_timestamp,
                )
            )


@manage_errors
def get_texts_by_user(user_id):
    with psycopg2.connect(
        **DB_CONFIG, cursor_factory=psycopg2.extras.DictCursor,
    ) as con:
        with con.cursor() as cur:
            cur.execute(sql_queries.GET_TEXTS_BY_USER, (user_id,))
            return cur.fetchall()


@manage_errors
def create_user(user_id, firstname, lastname, joined, password):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            try:
                cur.execute(
                    sql_queries.CREATE_USER,
                    (user_id, firstname, lastname, joined, password)
                )
            except psycopg2.errors.UniqueViolation:
                return return_codes.USER_EXISTS


@manage_errors
def get_user(user_id):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                sql_queries.GET_USER,
                (user_id,)
            )
            return cur.fetchone()


@manage_errors
def update_user_last_connection(user_id, timestamp):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.UPDATE_USER_LAST_CONNECTION,
                (timestamp, user_id)
            )
