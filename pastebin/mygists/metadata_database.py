"""
Functions in this module assume that:

* a Postgres version >= 12 is used
* the following environment variables are defined:
    * METADATA_DB_DATABASE
    * METADATA_DB_USER
    * METADATA_DB_PASSWORD
    * METADATA_DB_HOST
    * METADATA_DB_PORT
"""
import psycopg2
import psycopg2.errors
import psycopg2.extensions
import psycopg2.extras

import postgres

CREATE_USERS_TABLE_SQL = """
CREATE TABLE users (
  user_id VARCHAR(40) PRIMARY KEY,
  first_name VARCHAR(40),
  last_name VARCHAR(40),
  joined_date DATE,
  last_connection_date DATE
);
"""

CREATE_TEXTS_TABLE_SQL = """
CREATE TABLE texts (
  text_id VARCHAR(10),
  text_path VARCHAR(255),
  created_by VARCHAR(40),
  creation_date DATE,
  expiration_date DATE,
);
"""


# parameters for connection retries
MAX_RETRIES = 9
BACKOFF_FACTOR = 0.3


class Metadata:
    def __init__(self):
        self.db = postgres.DB()

    def store_text(
        self,
        text_id,
        text_path,
        user_id,
        creation_timestamp,
        expiration_timestamp,
    ):
        with self.db.con.cursor() as cur:
            cur.execute(
                "INSERT INTO texts values (%s, %s, %s, %s);",
                (
                    text_id,
                    text_path,
                    user_id,
                    creation_timestamp,
                    expiration_timestamp,
                ),
            )

    def get_texts_by_user(self, username):
        with self.db.con.cursor(
            cursor_factory=psycopg2.extras.DictCursor
        ) as cur:
            cur.execute(
                "SELECT * FROM texts WHERE created_by = '%s';", (username,)
            )
            return cur.fetchall()
