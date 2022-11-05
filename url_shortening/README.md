# URL Shortening Application

## Requirements

### Functional requirements

We want an application that takes a URL as an input, and returns a short URL as
an output, called an alias. This is useful to facilitate sharing long URLs,
because they take much less space and are users make less errors when typing
them.

Upon accessing a short URL, the user is redirected to the original URL.

The short URL is generated automatically, but a user may choose to use its own
short URL. The application will verify the user-defined short URL is not
already taken, and is long enough.

Short URLs will expire after a certain amount of time, but the user can also
choose the time interval before expiration.

A user can create an account, although this is not mandatory to use the
application. With an account, a user can review his URLs and manage them:
review, create, update, and delete.

We should have quotas and API rate limiters to prevent abuse of the
application.

### Non-functional requirements

Storage of long and short URLs should be very durable, with a very low risk of
the system losing data.

Users should be able to access the original URL from a short URL very quickly,
in less than a second.

Our application should be highly available, especially to let users be
redirected from a short URL to the original URL. The functionality that creates
short URLs may be unavailable for small time intervals.

## Capacity estimation

We carry out estimates using powers of ten. For example, if we indicated a
value of 10^2, it means we expect a value between 100 and 1000.

We will build a system that can support 10^7 (10 million) daily users.

We estimate there will be 10^7 short URLs created per day or 10^2 per second,
and that each URL will be accessed 10^2 times, leading to 10^9 reads per day or
10^4 per second.

If we store URLs for up to 5 years, we will store 10^10 URLs in total (10
billion).

If storing a URL and its alias takes 10^2 bytes, we will need up to 10^12 bytes
of storage (terabyte range).

Coming back to read and write throughput, there will be 10^2 bytes * 10^4 =
10^6 bytes (1 MB) per second of read traffic, and 10^4 (10 KB) of write
traffic.

## System API

All functions accept a username and an API key as optional parameters, for
users that have an account.

`create_url` creates an alias and has the parameters:
* url (string): Original URL to be shortened (required).
* ttl (int): Time-to-live for the URL, in hours, stored as an expiration
  timestamp in the database (optional).
* alias (string): Desired alias (optional).
* Returns: code indicating success or failure.

`get_url` maps an alias to the original URL:
* alias (string): Short URL (required).
* Returns (string): Original URL or null if alias does not exist.

`get_urls_by_user` retrieves the aliases created by a user:
* user_name (string): Username (required).
* Returns (list): List of URLs created by the user.

`delete_url` deletes an alias:
* alias (string): Short URL (required).
* Returns: code indicating success or failure.

## Data model

We need the following tables:

* users
    * user_name (string, primary key)
    * first_name (string)
    * last_name (string)
    * joined_on (timestamp)
    * password (string)
    * last_login (timestamp)

* urls
    * alias (string, primary key)
    * original (string)
    * created_by (string)
    * created_on (timestamp)
    * ttl (timestamp)

Given the estimated application throughput (tens of thousands of operations
per second) and data volume (several terabytes), a distributed key-value or
document store is appropriate.

We will shard the users table by `user_name` because it has unique values
(maximum cardinality). The value should be hashed to decrease the
probability of hot shards. Range-based sharding would not perform as well
because user names do not use the full range of possible strings.

The urls table will be sharded by alias. We can use range-based sharding
because all possible values for aliases are used.

To increase the performance of retrieving URLs created by a logged user, we
will create an index on the field `created_by` in the `urls` table.

## Short URL generation

We want to store 10 billion short URLs. If we use all ASCII letters (both upper
and lower cases), digits, hyphen, underscore and period characters, we need 6
characters (65^6 is approximately equal to 75 billion).

A simple solution would be to hash the original URL using an algorithm such as
MD5 or SHA, then convert it to a string. However, the resulting string would
exceed 6 characters, so we may truncate the string but risk having alias
collisions (several URLs having the same alias). To solve this, adding the user
ID to the original URL or an incrementing number (for non-logged users) would
solve the problem.

Another solution is to pre-generate URL aliases, store them in a database, and
get a key when a new alias is created. This solution will allow us to quickly
get an alias, and prevent any collision. When an alias is used, it should be
removed from the alias database to make sure it is not used again. ACID
transaction would help ensuring that an alias cannot be used but more than one
time. Instead of always querying the alias database to store a new URL, a few
aliases can be loaded into memory. If a server crashes, the aliases remaining
in memory will be wasted, but this is acceptable because we pre-generated
aliases in excess. The total storage necessary will be 1 byte * 6 characters *
75 billion aliases = 452 GB.

## High-level design

Our application will be presented as a website and as an API.

Our system will have, at a minimum, the following components:
* application servers run the website and the API, store and retrieve URL
  aliases
* general database servers store the users and aliases tables
* alias key database servers store the pre-generated aliases

We will keep application servers stateless, allowing us to scale the
application by adding more application servers. Load balancers will balance
traffic from clients to the cluster of application servers.

Since the application is read-heavy, caching would be beneficial. A cache
holding 20% of daily traffic would store 17GB of data (read throughput is 1MB
per second). This volume of data easily fits on a single server.

## Detailed design

We will build our system using the programming language Python. Python has
libraries that support REST API services, web servers, many database clients,
etc. so we will be able to build our whole system using this language.

The following sections contain only code highlights for brevity. The full code
is available in the directory named 'mytinyurl'.

### URL alias service

#### Generate and store aliases

We will pregenerate a list of URL alias and store them in a database that will
serve as the backend of a REST API key provider service.

Since the data size is modest (452 GB) and we need to strongly isolate queries
to the database (to avoid providing the same key more than once), a relational
database is a fine choice. We will use
[PostgreSQL](https://www.postgresql.org/), which is open-source and offers
great performance.

For the REST API, we will use the library
[FastAPI](https://fastapi.tiangolo.com/). FastAPI is simple to use and has a
great documentation.

The following code shows how to generate a list of URL aliases:

```python
import itertools
import random
import string


def generate_aliases(length=6):
    """
    Generates a list of aliases of the desired length, in random order.

    :param int length: Desired alias length.
    :returns (list(str)): Aliases.
    """
    alphabet = string.ascii_letters + string.digits + "-_."
    aliases = [
        ("".join(i),) for i in itertools.product(alphabet, repeat=length)
    ]
    random.shuffle(aliases)
    return aliases
```

We put aliases in 1-element tuples to facilitate loading them into the
database, using a function that expects tuples.

We shuffle the list of aliases so that we can later avoid serving them in a
predictable order, which is a security risk. The `random` module of the Python
standard library does not offer cryptographic-level randomization, but it's a
good start for a proof-of-concept system.

The PostgreSQL table that stores URL aliases can be generated with the query:

```
CREATE TABLE aliases (id VARCHAR(6));
```

The following snippet shows how to store aliases in the database:

```python
import psycopg2.extras


def store_aliases(aliases, con, page_size=10000):
    """
    Stores URL aliases in the database, in batches.

    :param list(str) aliases: Aliases to store.
    :param psycopg2.connection con: Psycopg2 connection object.
    :param int page_size: Alias batch size.
    :returns: None.
    """
    with con.cursor() as cur:
        cur.execute("TRUNCATE TABLE aliases;")
        psycopg2.extras.execute_batch(
            cur,
            "INSERT INTO aliases VALUES (%s);",
            aliases,
            page_size=page_size,
        )
        con.commit()
```

The function
[execute_batch()](https://www.psycopg.org/docs/extras.html#psycopg2.extras.execute_batch)
helps speed up the loading process by loading batches of records, leading to
fewer round-trips to the database server. The SQL query is parameterized, this
is why we put aliases in tuples in the function `generate_aliases()`.

#### Retrieve aliases

The URL alias service will provide aliases to the main URL shortening
application.

To prevent the same alias being used more than once, we will enforce a
[serializable isolation
level](https://www.postgresql.org/docs/current/transaction-iso.html), the
strongest isolation level. This means that some queries to the database will
fail because they are done concurrently, so we will setup query retries with
[exponential
backoff](https://cloud.google.com/iot/docs/how-tos/exponential-backoff).

To amortize the cost of querying the database, we will retrieve batches of
aliases and store them in memory. This means that a failure (server crash,
power outage, etc.) could lead to lost aliases, but this is not a problem
because we generated a large excess of aliases.

The following code defines a `DB` class that will help us manage connections to
PostgreSQL:

```python
import os

import psycopg2
import psycopg2.extensions


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
``` 

We set the default isolation level for our application to the value defined in
the constant `psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE`, but leave the
opportunity to the user to change it.

Database connection parameters may be defined in the following environment
variables:

* ALIAS_DB_HOST: Database host, i.e. URL or IP address.
* ALIAS_DB_PORT: Port the database server listens to.
* ALIAS_DB_DATABASE: Database name.
* ALIAS_DB_USER: Username for authentication.
* ALIAS_DB_PASSWORD: Password for authentication.

The following code implements the function to load batches of aliases in
memory:

```python
import time

import psycopg2.errors

MAX_RETRIES = 10
BACKOFF_FACTOR = 0.3


def get_aliases_batch(con, size=1000):
    """
    Gets a batch of aliases from the database, and removes them from the
    database.

    :param psycopg2.connection con: Psycopg2 connection object.
    :param int size: Batch size.
    :returns (list(str)): Batch of aliases.
    """
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
```

The function `get_aliases()` takes a `psycopg2` [connection
object](https://www.psycopg.org/docs/connection.html#the-connection-class) such
as the one managed by the class `DB` and retrieves a batch of aliases from the
database. To avoid reusing aliases, we delete and return their values.

We enclose the database query in a `try except` block and catch serialization
errors with the error `psycopg2.errors.SerializationFailure`. If such an error
occurs, we retry the query up to 10 times with exponentially longer wait times
between queries.

We now have all the tools to write our REST API endpoint. It's quite simple:

```python
from fastapi import FastAPI

import postgres  # defines the DB class and get_aliases_batch function


class Batch:
    def __init__(self, size=1000):
        print("connecting to database")
        self.db = postgres.DB()
        self.size = size
        self.items = []
        self.load_batch()

    def load_batch(self):
        if len(self.items) > 0:
            return
        if self.db.con.closed:
            self.db.connect()
        self.items = postgres.get_aliases_batch(self.db.con, self.size)

    def get_alias(self):
        if len(self.items) == 0:
            self.load_batch()
        return self.items.pop()


app = FastAPI()
batch = Batch(1000)


@app.get("/get-alias")
def get_alias():
    return {"alias": batch.get_alias()}
```

The class `DB` and the function `get_aliases_batch` are defined in a module
named `postgres.py`.

We define a class `Batch` that retrieves a batch of URL aliases from the
database and holds them in memory as a list named `self.items`. When list is
empty, a new batch of aliases is requested.

Our API has a single endpoint located at `/get-alias`, which returns a single
alias.

### URL shortening service

#### Data storage

We will store `urls` and `users` tables in a document database. Many databases
support the document model, we will use [CouchDB](https://couchdb.apache.org/)
because of the following attributes:

* can be deployed in a cluster and
  [sharded](https://docs.couchdb.org/en/3.2.2-docs/cluster/sharding.html), a
  requirement based on our calculations on data throughput
* query interface via
  [views](https://docs.couchdb.org/en/3.2.2-docs/ddocs/views/index.html) that
  are indexed
* Python client [library](https://pypi.org/project/CouchDB3/)

The tables `users` needs to be indexed by `user_name` and the `urls` needs to
be indexed by `alias`. These fields are the primary key for records and
contain unique values. CouchDB creates an index on the [`_id`
field](https://docs.couchdb.org/en/3.2.2-docs/intro/overview.html#document-storage)
of a document, therefore  will store the user name in the `_id` field of the
`users` table and the URL alias in the `_id` field of the the `urls` table.

Now, let's focus on functions run by our application. An important fact to
consider is that to update a document in CouchDB, the application has to
provide the revision number, stored in the `_rev` field. If the value does not
match the current revision, the update is rejected. Our code currently does not
handle such rejections. More info
[here](https://docs.couchdb.org/en/3.2.2-docs/api/document/common.html?highlight=update%20existing%20document#updating-an-existing-document).

The application relies on environment variables:

* APP_DB_HOST: URL the CouchDB client connects to.
* APP_DB_PORT: Port the CouchDB client connects to.
* APP_DB_USER: Username to authenticate to CouchDB.
* APP_DB_PASSWORD: Password to authenticate to CouchDB.
* APP_DB_DATABASE_USERS: Name of the database that stores documents for users.
* APP_DB_DATABASE_URLS: Name of the database that stores documents for URLs.

We create a custom class `Client` to manage all database functions. Here is the
constructor method for this class (we will detail all methods later):

```python
import os

import couchdb3


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
```

The following functions get user information and create a new user. Since
the `couchdb3` library does not automatically serialize `datetime` objects,
we add two functions to do it. All these functions are methods of the
`Client` class, the above code is omitted for brevity.

```python
import datetime

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


class Client:

    def str_to_datetime(self, s, fmt=DATETIME_FMT):
        return datetime.datetime.strptime(s, fmt)

    def datetime_to_str(self, d, fmt=DATETIME_FMT):
        return d.strftime(fmt)

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
```

We define a method to store a new URL:

```python
class Client:

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
```

We create a view on the field `created_by` of the `users` table, to
allow efficient query of short URLs created by a logged user. The map function
of the view is very simple, it takes a document as an input and emits the field
`created_by` as a key, with no value. CouchDB will create a index on
`created_by`.

```python
URLS_BY_USER_VIEW = """
function(doc) {
  emit(doc.created_by, null);
}
"""


class Client:

    def create_urls_users_view(self, view_func=URLS_BY_USER_VIEW):
        design_doc = self.urls.get_design("urls")
        if design_doc is None:
            design_doc = {
                "_id": "_design/urls",
                "language": "javascript",
                "views": {"created_by": {"map": view_func}}
            }
        else:
            design_doc.update({"views": {"created_by": {"map": view_func}}})
        self.urls.save(design_doc)
```

The following methods implement common read queries of our application:

```python
class Client:

    def get_url(self, alias):
        result = self.urls.get(alias)
        if result is not None:
            return result["original"]

    def get_urls_by_user(self, user_name):
        result = self.urls.view(
            "urls", "created_by", key=json.dumps(user_name), include_docs=True,
        )
        if result["total_rows"] == 0:
            return []
        docs = [row["doc"] for row in result["rows"]]
        for d in docs:
            d["created_on"] = self.str_to_datetime(d["created_on"])
            d["ttl"] = self.str_to_datetime(d["ttl"])
        return docs
```

Finally, we update the timestamp of the last login of a user, when they login
to the application:

```python
class Client:

    def update_user_last_login(self, user_name):
        now = self.datetime_to_str(datetime.datetime.now())
        doc = self.users.get(user_name)
        if doc is not None:
            doc.update({"last_login": now})
            self.users.save(doc)
```

#### Frontend

Our URL shortening service has a web application frontend. We will use
[Flask](https://flask.palletsprojects.com/en/2.2.x/), a minimalistic and
Python-based web development framework that contains all the features we need
for this project.

To create a URL alias, the user can fill the following HTML form (the rest of
the HTML page is omitted for brevity):

```
<form method="post">
    <label for="longurl">Long URL</label>
    <input name="longurl" id="longurl" required>
    <label for="custom-alias">Custom alias (optional)</label>
    <input name="custom-alias" id="custom-alias">
    <label for="ttl">Expire after</label>
    <select name="ttl" id="ttl">
      <option value="1h">1 hour</option>
      <option value="1d">1 day</option>
      <option value="1w" selected="selected" >1 week</option>
      <option value="1m">1 month</option>
      <option value="1y">1 year</option>
    </select>
    <input type="submit" value="Make short">
</form>
```

The form contents are processed by the following Flask app:

```python
import os
import secrets
from urllib.parse import quote_plus

import requests
from flask import (
    Flask,
    render_template,
    request,
)

from . import couchdb  # defines our custom couchdb functions

APP_URL = os.getenv("APP_URL")
TTL_TO_HOURS = {
    "1h": 1,
    "1d": 24,
    "1w": 24 * 7,
    "1m": 24 * 30,
    "1y": 24 * 365,
}

db_client = couchdb.Client()


def create_app():
    app = Flask(__name__)
    app.secret_key = secrets.token_hex()

    @app.route("/", methods=("GET", "POST"))
    def index():
        msg = None

        if request.method == "POST":
            long_url = request.form["longurl"]
            alias = request.form["custom-alias"]
            ttl = TTL_TO_HOURS[request.form["ttl"]]

            if alias:
                alias = quote_plus(alias)
                if db_client.get_url(alias) is not None:
                    msg = f"Error: alias '{alias}' already exists"
            else:
                alias_host = os.getenv("ALIAS_SERVICE_HOST")
                alias_port = os.getenv("ALIAS_SERVICE_PORT")
                alias = requests.get(
                    f"http://{alias_host}:{alias_port}/get-alias"
                ).json()["alias"]

            if msg is None:
                db_client.create_url(alias, long_url, username, ttl)
                msg = f"Created short URL: {APP_URL}/{alias}"

        return render_template("index.html", message=msg, myurls=user_urls)

    return app
```

If the request method is POST, this means the form was submitted, in which case
we retrieve the form contents. If a custom alias was proposed by the user, we
check if it already exists in the database and return an error if it does, else
we use the custom alias. If the user did not pass a custom alias, we fetch one
from the URL alias service. We then store the URL and its alias in the database
and return a message to the user indicating success.

The following code shows how to retrieve the original URL of an alias and
redirect the user to it (other lines of code are omitted for brevity):

```python
# imports are omitted

def create_app():
    # code omitted

    @app.route("/<alias>")
    def alias(alias):
        original_url = db_client.get_url(alias)
        if original_url is None:
            abort(404)
        return redirect(original_url)

    return app
```

The code simply retrieves the alias from the database and redirects the user to
it, or returns a 404 error if the alias does not exist.
