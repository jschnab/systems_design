from datetime import datetime

import psycopg2
import psycopg2.errors
import psycopg2.extras

from . import return_codes
from . import sql_queries
from .config import config

DB_CONFIG = {
    "host": config["database"]["host"],
    "port": config["database"]["port"],
    "dbname": config["database"]["database"],
    "user": config["database"]["user"],
    "password": config["database"]["password"],
}
DEFAULT_USER = config["app"]["default_user"]


def setup_database_objects():
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(sql_queries.CREATE_TABLE_USERS)
            cur.execute(sql_queries.CREATE_TABLE_TEXTS)
            cur.execute(sql_queries.CREATE_INDEX_TEXTS_USERID)
            cur.execute(sql_queries.CREATE_INDEX_TEXTS_USERIP)
            cur.execute(sql_queries.CREATE_INDEX_TEXTS_CREATION)
            cur.execute(sql_queries.INSERT_ANONYMOUS_USER, (DEFAULT_USER,))


def put_text_metadata(
    text_id, user_id, user_ip, creation_timestamp, expiration_timestamp,
):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.INSERT_TEXT,
                (
                    text_id,
                    f"{config['text_storage']['s3_bucket']}/{text_id}",
                    user_id,
                    user_ip,
                    creation_timestamp,
                    expiration_timestamp,
                ),
            )


def mark_text_for_deletion(text_id):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.MARK_TEXT_FOR_DELETION, (text_id,)
            )


def mark_text_deleted(text_id, deletion_timestamp):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.MARK_TEXT_DELETED, (deletion_timestamp, text_id)
            )


def get_texts_by_user(user_id):
    with psycopg2.connect(
        **DB_CONFIG, cursor_factory=psycopg2.extras.DictCursor,
    ) as con:
        with con.cursor() as cur:
            cur.execute(sql_queries.GET_TEXTS_BY_USER, (user_id,))
            return cur.fetchall()


def create_user(user_id, firstname, lastname, password):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            try:
                now = datetime.now()
                cur.execute(
                    sql_queries.CREATE_USER,
                    (user_id, firstname, lastname, now, password),
                )
            except psycopg2.errors.UniqueViolation:
                return return_codes.USER_EXISTS
    return return_codes.OK


def get_user(user_id):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql_queries.GET_USER, (user_id,))
            return cur.fetchone()


def update_user_last_connection(user_id, timestamp):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.UPDATE_USER_LAST_CONNECTION, (timestamp, user_id)
            )


def count_recent_texts_by_user(user_id, user_ip):
    with psycopg2.connect(
        **DB_CONFIG, cursor_factory=psycopg2.extras.DictCursor,
    ) as con:
        with con.cursor() as cur:
            if user_id == DEFAULT_USER:
                cur.execute(sql_queries.COUNT_TEXTS_ANONYMOUS, (user_ip,))
            else:
                cur.execute(sql_queries.COUNT_TEXTS_USER, (user_id,))
            return cur.fetchone()["quota"]


def get_texts_for_deletion():
    with psycopg2.connect(
            **DB_CONFIG, cursor_factory=psycopg2.extras.DictCursor
    ) as con:
        with con.cursor() as cur:
            cur.execute(sql_queries.GET_TEXTS_FOR_DELETION)
            return cur.fetchall()
