import psycopg2
import psycopg2.errors
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


def delete_text_metadata(text_id):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(sql_queries.DELETE_TEXT, (text_id,))


def get_texts_by_user(user_id):
    with psycopg2.connect(
        **DB_CONFIG, cursor_factory=psycopg2.extras.DictCursor,
    ) as con:
        with con.cursor() as cur:
            cur.execute(sql_queries.GET_TEXTS_BY_USER, (user_id,))
            return cur.fetchall()


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
    return return_codes.OK


def get_user(user_id):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                sql_queries.GET_USER,
                (user_id,)
            )
            return cur.fetchone()


def update_user_last_connection(user_id, timestamp):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.UPDATE_USER_LAST_CONNECTION,
                (timestamp, user_id)
            )
