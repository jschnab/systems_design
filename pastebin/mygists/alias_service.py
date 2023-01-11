import time

import psycopg2
import psycopg2.errors
import psycopg2.extensions as pg_ext
import psycopg2.extras
from fastapi import FastAPI

from config import config

# parameters for connection retries
MAX_RETRIES = 9
BACKOFF_FACTOR = 0.3

DB_CONFIG = {
    "host": config["alias_service"]["db_host"],
    "port": config["alias_service"]["db_port"],
    "database": config["alias_service"]["db_database"],
    "user": config["alias_service"]["db_user"],
    "password": config["alias_service"]["db_password"],
}


class Batch:
    def __init__(self, size=1000):
        print("connecting to database")
        self.size = size
        self.items = []
        self.load_batch()

    def load_batch(self):
        if len(self.items) > 0:
            return
        print("getting new batch of aliases")
        with psycopg2.connect(**DB_CONFIG) as con:
            con.isolation_level = pg_ext.ISOLATION_LEVEL_SERIALIZABLE
            with con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                retry = True
                retries = MAX_RETRIES
                while retry and retries >= 0:
                    try:
                        cur.execute(
                            (
                                "DELETE FROM aliases WHERE id in "
                                "(SELECT id FROM aliases LIMIT %s) "
                                "RETURNING *;"
                            ),
                            (self.size,)
                        )
                        self.items = [row["id"] for row in cur.fetchall()]
                        retry = False
                    except psycopg2.errors.SerializationFailure:
                        retries -= 1
                        time.sleep(
                            BACKOFF_FACTOR * 2 ** (MAX_RETRIES - retries)
                        )

    def get_alias(self):
        if len(self.items) == 0:
            self.load_batch()
        return self.items.pop()


app = FastAPI()
batch = Batch(1000)


@app.get("/get-alias")
def get_alias():
    return {"alias": batch.get_alias()}
