"""
Functions in this module assume that a Postgres version >= 12 is used
"""

import os

import psycopg2
import psycopg2.errors
import psycopg2.extensions
import psycopg2.extras

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
        self.host = host
        self.port = port
        self.dbname = database
        self.user = user
        self.password = password
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
