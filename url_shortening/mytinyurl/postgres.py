"""
Functions in this module assume that:

* a Postgres version >= 12 is used
* the following environment variables are defined:
    * ALIAS_DB_DATABASE
    * ALIAS_DB_USER
    * ALIAS_DB_PASSWORD
    * ALIAS_DB_HOST
    * ALIAS_DB_PORT
"""
import itertools
import os
import random
import string
import time

import psycopg2
import psycopg2.errors
import psycopg2.extensions
from psycopg2 import extras

CREATE_ALIASES_TABLE_SQL = """
CREATE TABLE aliases (id VARCHAR(6));
"""

# parameters for connection retries
MAX_RETRIES = 9
BACKOFF_FACTOR = 0.3


class DB:
    def __init__(
        self,
        host=None,
        port=None,
        database=None,
        user=None,
        password=None,
        isolation_level=psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,
    ):
        self.host = host or os.getenv("ALIAS_DB_HOST")
        self.port = port or os.getenv("ALIAS_DB_PORT")
        self.dbname = database or os.getenv("ALIAS_DB_DATABASE")
        self.user = user or os.getenv("ALIAS_DB_USER")
        self.password = password or os.getenv("ALIAS_DB_PASSWORD")
        self.isolation_level = isolation_level
        self.connect()

    def connect(self):
        con = psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
        )
        con.isolation_level = self.isolation_level
        self.con = con


def generate_aliases(length=6):
    alphabet = string.ascii_letters + string.digits + "-_."

    # Make tuples of single element to insert easily into database.
    aliases = [
        ("".join(i),) for i in itertools.product(alphabet, repeat=length)
    ]

    random.shuffle(aliases)
    return aliases


def store_aliases(aliases, con, page_size=10000):
    with con.cursor() as cur:
        cur.execute("TRUNCATE TABLE aliases;")
        extras.execute_batch(
            cur,
            "INSERT INTO aliases VALUES (%s);",
            aliases,
            page_size=page_size,
        )
        con.commit()


def get_aliases_batch(con, size=1000):
    with con.cursor() as cur:
        retry = True
        retries = MAX_RETRIES
        while retry and retries >= 0:
            try:
                cur.execute(
                    (
                        "DELETE FROM aliases where id in "
                        "(select id from aliases limit %s) RETURNING *;"
                    ),
                    (size,)
                )
                result = [row[0] for row in cur.fetchall()]
                con.commit()
                retry = False
            except psycopg2.errors.SerializationFailure:
                retries -= 1
                time.sleep(BACKOFF_FACTOR * 2 ** (MAX_RETRIES - retries))
    return result


def generate_aliases_run():
    print("generating aliases")
    aliases = generate_aliases(4)
    print("connecting to database")
    db = DB(isolation_level=psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)
    try:
        print("create aliases table if not exists")
        with db.con.cursor() as cur:
            cur.execute(CREATE_ALIASES_TABLE_SQL)
            db.con.commit()
        print("storing aliases to database")
        store_aliases(aliases, db.con)
        print("success")
    except Exception as e:
        print(e)
    finally:
        db.con.close()
