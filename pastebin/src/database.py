from contextlib import contextmanager
from datetime import datetime, timedelta

import mysql.connector

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
DEFAULT_USER = config["app"]["default_user"]
MAX_CONNECT_FAIL = 3
USER_LOCK_TIMEOUT = 15  # minutes

con_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="pastebin",
    pool_size=config["database"]["pool_size"],
    **DB_CONFIG,
)


@contextmanager
def connect(dictionary=False):
    con = con_pool.get_connection()
    cur = con.cursor(dictionary=dictionary)
    try:
        yield cur
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        cur.close()
        con.close()


def setup_database_objects():
    with connect() as cur:
        cur.execute(sql_queries.CREATE_TABLE_USERS)
        cur.execute(sql_queries.CREATE_ANONYMOUS_USER, (DEFAULT_USER,))
        cur.execute(sql_queries.CREATE_TABLE_USER_CONNECTIONS)
        cur.execute(sql_queries.CREATE_INDEX_USER_CONNECT_TS)
        cur.execute(sql_queries.CREATE_TABLE_TEXTS)
        cur.execute(sql_queries.CREATE_INDEX_TEXTS_USERID)
        cur.execute(sql_queries.CREATE_INDEX_TEXTS_USERIP)
        cur.execute(sql_queries.CREATE_INDEX_TEXTS_CREATION)


def put_text_metadata(
    text_id, user_id, user_ip, creation_timestamp, expiration_timestamp,
):
    with connect() as cur:
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
    with connect() as cur:
        cur.execute(
            sql_queries.MARK_TEXT_FOR_DELETION, (text_id,)
        )


def mark_text_deleted(text_id, deletion_timestamp):
    with connect() as cur:
        cur.execute(
            sql_queries.MARK_TEXT_DELETED, (deletion_timestamp, text_id)
        )


def get_texts_by_user(user_id):
    with connect(dictionary=True) as cur:
        cur.execute(sql_queries.GET_TEXTS_BY_USER, (user_id,))
        return cur.fetchall()


def create_user(user_id, firstname, lastname, password):
    with connect() as cur:
        try:
            now = datetime.now()
            cur.execute(
                sql_queries.CREATE_USER,
                (user_id, firstname, lastname, now, password),
            )
        except mysql.connector.IntegrityError:
            return return_codes.USER_EXISTS
    return return_codes.OK


def get_user(user_id):
    with connect(dictionary=True) as cur:
        cur.execute(sql_queries.GET_USER, (user_id,))
        return cur.fetchone()


def count_recent_texts_by_user(user_id, user_ip):
    with connect(dictionary=True) as cur:
        if user_id == DEFAULT_USER:
            cur.execute(sql_queries.COUNT_TEXTS_ANONYMOUS, (user_ip,))
        else:
            cur.execute(sql_queries.COUNT_TEXTS_USER, (user_id,))
        return cur.fetchone()["quota"]


def get_texts_for_deletion():
    with connect() as cur:
        cur.execute(sql_queries.GET_TEXTS_FOR_DELETION)
        return cur.fetchall()


def get_user_by_text(text_id):
    with connect(dictionary=True) as cur:
        cur.execute(sql_queries.GET_USER_BY_TEXT, (text_id,))
        return cur.fetchone()


def user_is_locked(user_id):
    with connect(dictionary=True) as cur:
        cur.execute(sql_queries.GET_RECENT_USER_CONNECTIONS, (user_id,))
        recent_connects = cur.fetchall()

    fails = 0
    for rc in recent_connects:
        if rc["success"]:
            break
        fails += 1

    lock_cutoff = datetime.now() - timedelta(minutes=USER_LOCK_TIMEOUT)
    if fails >= MAX_CONNECT_FAIL and recent_connects[0]["ts"] > lock_cutoff:
        return True

    return False


def record_user_connect(user_id, user_ip, success):
    with connect() as cur:
        cur.execute(
            sql_queries.RECORD_USER_CONNECT,
            (user_id, user_ip, success)
        )
