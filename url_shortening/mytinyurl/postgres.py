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


CREATE_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
  user_name VARCHAR(20) PRIMARY KEY,
  first_name VARCHAR(40),
  last_name VARCHAR(40),
  password VARCHAR(255),
  joined_on TIMESTAMP,
  last_login TIMESTAMP
);
"""


CREATE_URLS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS urls (
    alias VARCHAR(10) PRIMARY KEY,
    original VARCHAR,
    created_by VARCHAR(20),
    created_on TIMESTAMP,
    ttl TIMESTAMP
);
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


def create_url(alias, original, user_name, con, ttl=24):
    now = datetime.datetime.now()
    with con.cursor() as cur:
        cur.execute(
            (
                "INSERT INTO urls "
                "(alias, original, created_by, created_on, ttl) "
                "VALUES (%s, %s, %s, %s, %s);"
            ),
            (
                alias,
                original,
                user_name,
                now,
                now + datetime.timedelta(hours=ttl)
            ),
        )
        con.commit()


def get_url(alias, con):
    with con.cursor() as cur:
        cur.execute(
            "SELECT original from urls where alias = %s;",
            (alias,),
        )
        result = cur.fetchone()
    if result is not None:
        return result[0]


def delete_url(alias, con):
    with con.cursor() as cur:
        cur.execute(
            "DELETE FROM urls where alias = %s;",
            (alias,)
        )
        con.commit()


def test_create_alias():
    print("connecting to database")
    con = connect()
    try:
        print("create users and urls tables if not exist")
        with con.cursor() as cur:
            cur.execute(CREATE_USERS_TABLE_SQL)
            cur.execute(CREATE_URLS_TABLE_SQL)
            con.commit()
        print("getting aliases batch")
        aliases = get_aliases_batch(con, size=10)
        print("creating aliases")
        create_url(
            "https://www.facebook.com",
            "jschnab",
            aliases,
            con
        )
        create_url(
            (
                "https://flask.palletsprojects.com/en/2.0.x/quickstart/"
                "#a-minimal-application"
            ),
            "jschnab",
            aliases,
            con,
            ttl=24*7,
        )
        print("success")
    except Exception as e:
        print(e)
    finally:
        con.close()


def test_get_original_urls():
    print("connecting to database")
    con = connect()
    try:
        print("getting original url from alias")
        print(get_url("kKNQ", con))
        print(get_url("j93y", con))
        print(get_url("-sqK", con))
        print(get_url("gLqn", con))
    except Exception as e:
        print(e)
    finally:
        con.close()


def delete_expired_aliases(con):
    with con.cursor() as cur:
        cur.execute(
            "DELETE from urls where ttl < %s;",
            (datetime.datetime.now() + datetime.timedelta(days=1),)
        )
        con.commit()


def test_delete_expired_aliases():
    print("getting connection")
    con = connect()
    try:
        print("deleting expired aliases")
        delete_expired_aliases(con)
        print("success")
    except Exception as e:
        print(e)
    finally:
        con.close()


def test_delete_alias():
    print("connecting to database")
    con = connect()
    try:
        print("deleting url")
        delete_url("kKNQ", con)
        print("success")
    except Exception as e:
        print(e)
    finally:
        con.close()


def register_user(username, firstname, lastname, password):
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE user_name = %s;", (username,)
            )
            if cur.fetchone() is not None:
                return f"Username {username} already exists"
            cur.execute(
                (
                    "INSERT INTO users "
                    "(user_name, first_name, last_name, password, joined_on) "
                    "VALUES (%s, %s, %s, %s, %s);"
                ),
                (
                    username,
                    firstname,
                    lastname,
                    password,
                    datetime.datetime.now(),
                )
            )
            con.commit()
    except Exception as e:
        print(e)
        return "Error during user registration"
    finally:
        con.close()


def get_user(username):
    con = connect()
    try:
        with con.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(
                "select * from users where user_name = %s;", (username,)
            )
            result = cur.fetchone()
            if result is not None:
                cur.execute(
                    "update users set last_login = %s where user_name = %s;",
                    (datetime.datetime.now(), username)
                )
                con.commit()
            return result
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


def main():
    test_create_alias()


if __name__ == "__main__":
    main()
