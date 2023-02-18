import contextlib
import os
import sqlite3
import stat
import time

from .config import CONFIG

CACHE_DIR = CONFIG["local_disk_cache"]["cache_dir"]
DB_NAME = "db.sq3"
MAX_CACHE_SIZE = CONFIG["local_disk_cache"].getint("max_size")
FILE_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP

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
    def __init__(
        self,
        cache_dir=CACHE_DIR,
        db_name=DB_NAME,
        max_cache_size=MAX_CACHE_SIZE,
    ):
        self.cache_dir = cache_dir
        self.db_name = db_name
        self.max_cache_size = max_cache_size
        self.db_path = os.path.join(self.cache_dir, self.db_name)

        if os.path.isdir(self.cache_dir) and self.db_name in os.listdir(
            self.cache_dir
        ):
            self.current_size = self.start_cache_size()
        else:
            os.makedirs(self.cache_dir, mode=FILE_PERMISSIONS, exist_ok=True)
            self.create_db_file()
            self.setup_database()
            self.current_size = 0

    def file_descriptor(self, path):
        return os.open(path, os.O_RDWR | os.O_CREAT, FILE_PERMISSIONS)

    def create_db_file(self):
        with sqlite3.connect(self.db_path):
            pass
        os.chmod(self.db_path, FILE_PERMISSIONS)

    def start_cache_size(self):
        return sum(
            self.size_on_disk(fi)
            for fi in os.listdir(self.cache_dir)
            if fi != self.db_name
        )

    def size_on_disk(self, key):
        return os.path.getsize(os.path.join(self.cache_dir, key))

    def execute_query(self, query, params=None):
        params = params or tuple()
        with contextlib.closing(
            sqlite3.connect(self.db_path, isolation_level=None)
        ) as con:
            with contextlib.closing(con.cursor()) as cur:
                rows = cur.execute(query, params).fetchall()
        return rows

    def setup_database(self):
        self.execute_query(CREATE_TABLE)
        self.execute_query(CREATE_INDEX)

    def key_exists(self, key):
        return self.execute_query(KEY_EXISTS, (key,))[0][0]

    def refresh_timestamp(self, key):
        self.execute_query(UPDATE_TIMESTAMP, (int(time.time()), key))

    def set(self, key, value):
        print("calling disk_cache.set()")
        file_path = os.path.join(self.cache_dir, key)
        with open(self.file_descriptor(file_path), "wb") as f:
            f.write(value)
        if not self.key_exists(key):
            print("disk_cache.set() setting key:", key)
            self.execute_query(SET_KEY, (key, int(time.time())))
            self.current_size += self.size_on_disk(key)
            while self.current_size > self.max_cache_size:
                self.evict()
        else:
            print("disk_cache.set() refreshing key:", key)
            self.refresh_timestamp(key)
        return file_path

    def get_value(self, key):
        print("calling disk_cache.get_value()")
        if self.key_exists(key):
            self.refresh_timestamp(key)
            with open(os.path.join(self.cache_dir, key), "rb") as f:
                return f.read()

    def get_path(self, key):
        print("calling disk_cache.get_path()")
        if self.key_exists(key):
            print("disk_cache.get_path() key exists:", key)
            self.refresh_timestamp(key)
            return os.path.join(self.cache_dir, key)

    def evict(self):
        if self.current_size == 0:
            return
        lru_key = self.execute_query(LRU_KEY)[0][0]
        self.current_size -= self.size_on_disk(lru_key)
        os.remove(os.path.join(self.cache_dir, lru_key))
        self.execute_query(DELETE_KEY, (lru_key,))
