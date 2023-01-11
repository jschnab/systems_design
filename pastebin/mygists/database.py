import psycopg2
import psycopg2.errors
import psycopg2.extensions
import psycopg2.extras

from . import s3
from . import sql_queries
from .config import config

DB_CONFIG = {
    "host": config["database"]["host"],
    "port": config["database"]["port"],
    "database": config["database"]["database"],
    "user": config["database"]["user"],
    "password": config["database"]["password"],
}


def put_text(
    text_id,
    text_body,
    user_id,
    creation_timestamp,
    expiration_timestamp,
):
    s3.put_text(key=text_id, text_body=text_body)
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


def get_texts_by_user(user_id):
    with psycopg2.connect(
        **DB_CONFIG, cursor_factory=psycopg2.extras.DictCursor,
    ) as con:
        with con.cursor() as cur:
            cur.execute(sql_queries.GET_TEXTS_BY_USER, (user_id,))
            return cur.fetchall()


def create_user(user_id, firstname, lastname, joined, password):
    with psycopg2.connect(**DB_CONFIG) as con:
        con.isolation_level = psycopg2.extensions.ISOLATION_LEVEL_SERIALIZATION
        with con.cursor() as cur:
            cur.execute(
                sql_queries.CREATE_USER,
                (user_id, firstname, lastname, joined, password)
            )


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
