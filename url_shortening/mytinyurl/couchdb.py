import datetime
import json
import os

import couchdb3

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"

URLS_BY_USER_VIEW = """
function(doc) {
  var
    key = doc.created_by,
    value = doc;
  emit(key, value);
}
"""


class Client:
    def __init__(self):
        self.host = os.getenv("APP_DB_HOST", "localhost")
        self.port = int(os.getenv("APP_DB_PORT", 5984))
        self.db_users = os.getenv("APP_DB_DATABASE_USERS")
        self.db_urls = os.getenv("APP_DB_DATABASE_URLS")
        self.client = couchdb3.Server(
            f"{self.host}:{self.port}",
            user=os.getenv("APP_DB_USER"),
            password=os.getenv("APP_DB_PASSWORD"),
        )
        if self.db_users not in self.client:
            self.client.create(self.db_users)
        self.users = self.client.get(self.db_users)
        if self.db_urls not in self.client:
            self.client.create(self.db_urls)
        self.urls = self.client.get(self.db_urls)

    def str_to_datetime(self, s, fmt=DATETIME_FMT):
        return datetime.datetime.strptime(s, fmt)

    def datetime_to_str(self, d, fmt=DATETIME_FMT):
        return d.strftime(fmt)

    def create_urls_users_view(self, view_func=URLS_BY_USER_VIEW):
        design_doc = self.urls.get_design("urls")
        if design_doc is None:
            design_doc = {
                "_id": "_design/urls",
                "language": "javascript",
                "views": {"created_by": {"map": view_func}}
            }
        else:
            design_doc.update({"views": {"urls": {"map": view_func}}})
        self.urls.save(design_doc)

    def create_url(self, alias, original, user_name, ttl):
        now = datetime.datetime.now()
        doc = {
            "_id": alias,
            "original": original,
            "created_by": user_name,
            "created_on": self.datetime_to_str(now),
            "ttl": self.datetime_to_str(
                now + datetime.timedelta(hours=ttl)
            ),
        }
        self.urls.save(doc)

    def get_url(self, alias):
        result = self.urls.get(alias)
        if result is not None:
            return result["original"]

    def register_user(self, user_name, first_name, last_name, password):
        if self.get_user(user_name) is not None:
            return
        self.users.save(
            {
                "_id": user_name,
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
                "joined_on": self.datetime_to_str(datetime.datetime.now()),
            }
        )

    def get_user(self, user_name):
        doc = self.users.get(user_name)
        if doc is None:
            return
        last_login = None
        if "last_login" in doc:
            last_login = self.str_to_datetime(doc["last_login"])
        doc.update(
            {
                "joined_on": self.str_to_datetime(doc["joined_on"]),
                "last_login": last_login,
            }
        )
        return doc

    def get_urls_by_user(self, user_name):
        result = self.urls.view(
            "urls", "created_by", key=json.dumps(user_name)
        )
        if result["total_rows"] == 0:
            return []
        values = [row["value"] for row in result["rows"]]
        for v in values:
            v["created_on"] = self.str_to_datetime(v["created_on"])
            v["ttl"] = self.str_to_datetime(v["ttl"])
        return values

    def update_user_last_login(self, user_name):
        now = self.datetime_to_str(datetime.datetime.now())
        doc = self.users.get(user_name)
        if doc is not None:
            doc.update({"last_login": now})
            self.users.save(doc)
