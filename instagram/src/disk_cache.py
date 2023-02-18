import contextlib
import os
import sqlite3
import time

from .config import CONFIG

CACHE_DIR = CONFIG["local_disk_cache"]["cache_dir"]
DB_NAME = "db.sq3"
DB_PATH = os.path.join(CACHE_DIR, DB_NAME)
MAX_CACHE_SIZE = CONFIG["local_disk_cache"].getint("max_size")

CREATE_TABLE = "CREATE TABLE cache (key text PRIMARY KEY, timestamp integer);"

CREATE_INDEX = "CREATE INDEX idx_cache_timestamp ON cache (timestamp);"

SET_KEY = "INSERT INTO cache values (?, ?);"

KEY_EXISTS = "SELECT EXISTS(SELECT 1 FROM cache WHERE key = ?);"

UPDATE_TIMESTAMP = "UPDATE cache SET timestamp = ? WHERE key = ?;"

LRU_KEY = """
SELECT key FROM cache
WHERE timestamp = (SELECT MIN(timestamp) FROM cache)
LIMIT 1
;"""

DELETE_KEY = "DELETE FROM cache WHERE key = ?;"


class DiskCache:
    def __init__(self):
        if os.path.isdir(CACHE_DIR) and DB_NAME in os.listdir(CACHE_DIR):
            self.current_size = self.start_cache_size()
        else:
            os.makedirs(CACHE_DIR, mode=0o770, exist_ok=True)
            self.setup_database()
            self.current_size = 0

    def start_cache_size(self):
        return sum(
            self.size_on_disk(fi) for fi in os.listdir(CACHE_DIR)
            if fi != DB_NAME
        )

    def size_on_disk(self, key):
        return os.path.getsize(os.path.join(CACHE_DIR, key))

    def execute_query(self, query, params=None):
        params = params or tuple()
        with contextlib.closing(sqlite3.connect(DB_PATH)) as con:
            with contextlib.closing(con.cursor()) as cur:
                rows = cur.execute(query, params).fetchall()
                con.commit()
        return rows

    def setup_database(self):
        self.execute_query(CREATE_TABLE)
        self.execute_query(CREATE_INDEX)

    def key_exists(self, key):
        return self.execute_query(KEY_EXISTS, (key,))[0][0]

    def refresh_timestamp(self, key):
        self.execute_query(UPDATE_TIMESTAMP, (int(time.time()), key))

    def set(self, key, value):
        file_path = os.path.join(CACHE_DIR, key)
        with open(file_path, "wb") as f:
            f.write(value)
        if not self.key_exists(key):
            self.execute_query(SET_KEY, (key, int(time.time())))
            self.current_size += self.size_on_disk(key)
            while self.current_size > MAX_CACHE_SIZE:
                self.evict()
        else:
            self.refresh_timestamp(key)
        return file_path

    def get_value(self, key):
        if self.key_exists(key):
            self.refresh_timestamp(key)
            with open(os.path.join(CACHE_DIR, key), "rb") as f:
                return f.read()

    def get_path(self, key):
        if self.key_exists(key):
            self.refresh_timestamp(key)
            return os.path.join(CACHE_DIR, key)

    def evict(self):
        if self.current_size == 0:
            return
        lru_key = self.execute_query(LRU_KEY)[0][0]
        self.current_size -= self.size_on_disk(lru_key)
        os.remove(os.path.join(CACHE_DIR, lru_key))
        self.execute_query(DELETE_KEY, (lru_key,))
