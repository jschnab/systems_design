import datetime
import os

import pymongo


class Client:
    def __init__(self):
        self.host = os.getenv("APP_DB_HOST", "localhost")
        self.port = int(os.getenv("APP_DB_PORT", 27017))
        self.db_name = os.getenv("APP_DB_DATABASE")
        self.coll_users = os.getenv("APP_DB_COLLECTION_USERS")
        self.coll_urls = os.getenv("APP_DB_COLLECTION_URLS")
        self.client = pymongo.MongoClient(self.host, self.port)
        self.db = self.client[self.db_name]
        self.users = self.db[self.coll_users]
        self.urls = self.db[self.coll_urls]

    def create_urls_users_index(self):
        self.urls.create_index(("created_by", pymongo.HASHED))

    def create_url(self, alias, original, user_name, ttl):
        now = datetime.datetime.now()
        doc = {
            "_id": alias,
            "original": original,
            "created_by": user_name,
            "created_on": now,
            "ttl": now + datetime.timedelta(hours=ttl),
        }
        self.urls.insert_one(doc)

    def get_url(self, alias):
        result = self.urls.find_one({"_id": alias}, {"_id": 0, "original": 1})
        if result is not None:
            return result["original"]

    def register_user(self, user_name, first_name, last_name, password):
        self.users.insert_one(
            {
                "_id": user_name,
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
                "joined_on": datetime.datetime.now(),
            }
        )

    def get_user(self, user_name):
        return self.users.find_one({"_id": user_name})

    def get_urls_by_user(self, user_name):
        return list(self.urls.find({"created_by": user_name}))

    def update_user_last_login(self, user_name):
        now = datetime.datetime.now()
        self.users.update_one(
            {"_id": user_name}, {"$set": {"last_login": now}}
        )
