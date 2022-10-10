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
import datetime
import itertools
import os
import random
import string

import psycopg2
from psycopg2 import extras


CREATE_ALIASES_TABLE_SQL = """
CREATE TABLE aliases (id VARCHAR(6));
"""


def connect(database=None, user=None, password=None, host=None, port=None):
    con = psycopg2.connect(
        database=database or os.getenv("ALIAS_DB_DATABASE"),
        user=user or os.getenv("ALIAS_DB_USER"),
        password=password or os.getenv("ALIAS_DB_PASSWORD"),
        host=host or os.getenv("ALIAS_DB_HOST"),
        port=port or os.getenv("ALIAS_DB_PORT"),
    )
    return con


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
        cur.execute(
            (
                "DELETE FROM aliases where id in "
                "(select id from aliases limit %s) RETURNING *;"
            ),
            (size,)
        )
        result = [row[0] for row in cur.fetchall()]
        con.commit()
    return result


def generate_aliases_run():
    print("generating aliases")
    aliases = generate_aliases(4)
    print("connecting to database")
    con = connect()
    try:
        print("create aliases table if not exists")
        with con.cursor() as cur:
            cur.execute(CREATE_ALIASES_TABLE_SQL)
            con.commit()
        print("storing aliases to database")
        store_aliases(aliases, con)
        print("success")
    except Exception as e:
        print(e)
    finally:
        con.close()


def test_get_aliases_batch():
    con = connect()
    try:
        batch = get_aliases_batch(con, 10)
        print(batch[:10])
    except Exception as e:
        print(e)
    finally:
        con.close()


class DB:
    def __init__(self):
        self.con = connect()

    def get_url(self, alias):
        if self.con.closed:
            self.con = connect()
        return get_url(alias, self.con)

    def create_url(self, alias, original, user, ttl):
        if self.con.closed:
            self.con = connect()
        create_url(
            alias, original, user, self.con, ttl
        )
