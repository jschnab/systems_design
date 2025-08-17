import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import partial

import mysql.connector

from . import return_codes
from . import sql_queries
from .config import config
from .log import get_logger

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
LOGGER = get_logger()

connection_pool = None


def init_connection_pool():
    global connection_pool
    if connection_pool is None:
        LOGGER.info("Creating database connection pool")
        connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="pastebin",
            pool_size=config["database"]["pool_size"],
            **DB_CONFIG,
        )


def close_connection_pool():
    if connection_pool is not None:
        LOGGER.info("Closing database connection pool")
        n_closed = connection_pool._remove_connections()
        LOGGER.info(f"Closed {n_closed} database connections")


thread_pool = None


def init_thread_pool():
    global thread_pool
    if thread_pool is None:
        LOGGER.info("Creating database thread pool")
        thread_pool = ThreadPoolExecutor()


def close_thread_pool():
    if thread_pool is not None:
        LOGGER.info("Closing database thread pool")
        thread_pool.shutdown()


@contextmanager
def connect(db_config=DB_CONFIG, dictionary=False):
    con = connection_pool.get_connection()
    cur = con.cursor(dictionary=dictionary)
    try:
        yield cur
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        # Avoid 'OperationalError: MySQL Connection not available.'
        # when closing the connection.
        if con.is_connected():
            cur.close()
            con.close()


async def execute_in_thread_pool(query, args=None):
    with connect(dictionary=True) as cur:
        await asyncio.get_running_loop().run_in_executor(
            thread_pool,
            partial(
                cur.execute,
                query,
                args,
            ),
        )
        return cur.fetchall()


async def setup_database_objects(root_password):
    root_db_config = {
        "host": config["database"]["host"],
        "port": config["database"]["port"],
        "database": "mysql",
        "user": "root",
        "password": root_password,
    }
    with mysql.connector.connect(**root_db_config) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.CREATE_DATABASE.format(
                    database_name=config["database"]["database"],
                )
            )
            cur.execute(
                sql_queries.CREATE_DB_USER.format(
                    user_name=config["database"]["user"],
                    password=config["database"]["password"],
                )
            )
            cur.execute(
                sql_queries.CREATE_DB_USER_PERMISSIONS.format(
                    database_name=config["database"]["database"],
                    user_name=config["database"]["user"],
                )
            )
        con.commit()

    with mysql.connector.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(sql_queries.CREATE_TABLE_USERS)
            try:
                cur.execute(sql_queries.CREATE_ANONYMOUS_USER, (DEFAULT_USER,))
            except mysql.connector.IntegrityError:
                pass
            cur.execute(sql_queries.CREATE_TABLE_USER_CONNECTIONS)
            cur.execute(sql_queries.CREATE_INDEX_USER_CONNECT_TS)
            cur.execute(sql_queries.CREATE_TABLE_TEXTS)
            cur.execute(sql_queries.CREATE_INDEX_TEXTS_USERID)
            cur.execute(sql_queries.CREATE_INDEX_TEXTS_USERIP)
            cur.execute(sql_queries.CREATE_INDEX_TEXTS_CREATION)
        con.commit()


async def put_text_metadata(
    text_id,
    text_title,
    user_id,
    user_ip,
    creation_timestamp,
    expiration_timestamp,
    burn_after_reading,
):
    await execute_in_thread_pool(
        sql_queries.INSERT_TEXT,
        (
            text_id,
            text_title,
            f"{config['text_storage']['s3_bucket']}/{text_id}",
            user_id,
            user_ip,
            creation_timestamp,
            expiration_timestamp,
            burn_after_reading,
        ),
    )


async def mark_text_for_deletion(text_id):
    await execute_in_thread_pool(
        sql_queries.MARK_TEXT_FOR_DELETION, (text_id,)
    )


async def mark_text_deleted(text_id, deletion_timestamp):
    await execute_in_thread_pool(
        sql_queries.MARK_TEXT_DELETED, (deletion_timestamp, text_id)
    )


async def get_texts_by_owner(user_id):
    return await execute_in_thread_pool(
        sql_queries.GET_TEXTS_BY_OWNER, (user_id,)
    )


async def create_user(user_id, firstname, lastname, password):
    try:
        now = datetime.now()
        await execute_in_thread_pool(
            sql_queries.CREATE_USER,
            (user_id, firstname, lastname, now, password),
        )
    except mysql.connector.IntegrityError:
        return return_codes.USER_EXISTS
    return return_codes.OK


async def get_user(user_id):
    user = await execute_in_thread_pool(sql_queries.GET_USER, (user_id,))
    if user:
        return user[0]


async def count_recent_texts_by_anonymous_user(user_ip):
    return (
        (
            await execute_in_thread_pool(
                sql_queries.COUNT_TEXTS_ANONYMOUS, (user_ip,)
            )
        )[0]
    )["quota"]


async def count_recent_texts_by_logged_user(user_id):
    return (
        (
            await execute_in_thread_pool(
                sql_queries.COUNT_TEXTS_USER, (user_id,)
            )
        )[0]
    )["quota"]


async def get_texts_for_deletion():
    return await execute_in_thread_pool(sql_queries.GET_TEXTS_FOR_DELETION)


async def get_text_owner(text_id):
    # No guardrail for non-existant text ID, do not use with user input.
    return (
        (await execute_in_thread_pool(sql_queries.GET_TEXT_OWNER, (text_id,)))[
            0
        ]
    )["user_id"]


async def user_is_locked(user_id):
    recent_connects = await execute_in_thread_pool(
        sql_queries.GET_RECENT_USER_CONNECTIONS, (user_id,)
    )

    fails = 0
    for rc in recent_connects:
        if rc["success"]:
            break
        fails += 1

    lock_cutoff = datetime.now() - timedelta(minutes=USER_LOCK_TIMEOUT)
    if fails >= MAX_CONNECT_FAIL and recent_connects[0]["ts"] > lock_cutoff:
        return True

    return False


async def record_user_connect(user_id, user_ip, success):
    await execute_in_thread_pool(
        sql_queries.RECORD_USER_CONNECT, (user_id, user_ip, success)
    )


async def text_is_visible(text_id):
    return (
        await execute_in_thread_pool(sql_queries.TEXT_IS_VISIBLE, (text_id,))
    )[0]["is_visible"]


async def is_text_burn_after_reading(text_id):
    return (
        await execute_in_thread_pool(
            sql_queries.IS_TEXT_BURN_AFTER_READING, (text_id,)
        )
    )[0]["burn_after_reading"]
