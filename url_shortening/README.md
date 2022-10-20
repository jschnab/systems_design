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
of storage (1 TB).

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
* alias (string): Short URL.
* Returns (string): Original URL or null if alias does not exist.

`get_urls_by_user` retrieves the aliases created by a user:
* user_name (string): Username.
* Returns (list): List of URLs created by the user.

`delete_url` deletes an alias:
* alias (string): Short URL.
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

Given the estimated application throughput, a distributed key-value or document
store is appropriate.

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

## Detailed design

We will build our system using the programming language Python. Python has
libraries that support REST API services, web servers, many database clients,
etc. so we will be able to build our whole system using this language.

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
import string


def generate_aliases(length=6):
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
    with con.cursor() as curL
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

import postgres


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
            print("connecting to database")
            self.db.connect()
        print("getting new batch of aliases")
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
support the document model, we will use [MongoDB](https://www.mongodb.com/)
because of the following attributes:

* can be deployed in a cluster and
  [sharded](https://www.mongodb.com/docs/v4.4/core/sharded-cluster-shards/), a
  requirement based on our calculations on data volume
* support for [indexes](https://www.mongodb.com/docs/manual/indexes/)
* powerful yet simple [query
  interface](https://www.mongodb.com/docs/manual/tutorial/query-documents/)
* reliable Python client library,
  [PyMongo](https://pymongo.readthedocs.io/en/stable/)

With MongoDB, we don't need to create database or tables upfront. Any operation
on databases or tables will create them.

The tables `users` needs to be indexed by `user_name` and the `urls` needs to
be indexed by `alias`. Since these fields are the primary key for records and
contain unique values, and MongoDB always creates an index on the [`_id`
field](https://www.mongodb.com/docs/manual/core/document/#std-label-document-id-field)
of a document, we will store the user name in the `_id` field of the `users`
table and the URL alias in the `_id` field of the the `urls` table.

We also create an index on the field `created_by` of the `users` table, to
allow efficient query of short URLs created by a logged user. MongoDB supports
range and hash indexes, we will create a hash index because usernames may
cluster under some prefixes, depending on letters frequency in names:

```
db.urls.createIndex({"created_by": "hashed"})
```

Now, let's focus on functions run by our application. Creating a client using
PyMongo is simple, the following example connects to `mongos` running on the
local host and listening on port 27017.

```python
import pymongo

client = pymongo.MongoClient("localhost", 27017)
```

We define a function to register a new user, storing data in the database
`shorturls` and table `users`:

```python
import datetime


def register_user(client, user_name, first_name, last_name, password):
    """
    Registers a new user.

    :param pymongo.MongoClient: MongoDB client.
    :param str user_name: User login name.
    :param str first_name: User first name.
    :param str last_name: User last name.
    :param str password: Hashed password.
    :returns: None.
    """
    client.shorturls.users.insert_one(
        {
            "_id": user_name,
            "first_name": first_name,
            "last_name": last_name,
            "password": password,
            "joined_on": datetime.datetime.now(),
        }
    )
```

We define a function to store a new URL:

```python
import datetime


def create_url(client, alias, original, user_name, ttl):
    """
    Store a new URL.

    :param pymongo.MongoClient client: MongoDB client.
    :param str alias: Short URL.
    :param str original: Original URL.
    :param str user_name: Name of the user who created the URL.
    :param int ttl: Time-to-live, in hours.
    :returns: None.
    """
    now = datetime.datetime.now()
    doc = {
        "_id": alias,
        "original": original,
        "created_by": user_name,
        "created_on": now,
        "ttl": now + datetime.timedelta(hours=ttl),
    }
    client.shorturls.urls.insert_one(doc)
```

The following functions implement common read queries of our application:

```python
def get_url(client, alias):
    """
    Retrieve a long URL based on the alias.

    :param pymongo.MongoClient client: MongoDB client.
    :param str alias: Short URL.
    :returns (str|None): Original URL, or None if it does not exist.
    """
    result = client.shorturls.urls.find_one(
        {"_id": alias}, {"_id": 0, "original": 1}
    )
    if result is not None:
        return result["original"]


def get_user(client, user_name):
    """
    Checks if a user exists in the database.

    :param pymongo.MongoClient client: MongoDB client.
    :param str user_name: User login name.
    :returns (str|None): User name if exists, else None.
    """
    return client.shorturls.users.find_one({"_id": user_name})


def get_urls_by_user(client, user_name):
    """
    Get the list of URLs created by a user.

    :param pymongo.MongoClient client: MongoDB client.
    :param str user_name: User login name.
    :returns (list(str)): URLs created by a user.
    """
    return list(client.shorturls.urls.find({"created_by": user_name}))
```

Finally, we update the timestamp of the last login of a user, when they login
to the application:

```python
import datetime


def update_user_last_login(client, user_name):
    """
    Update the last user login timestamp.

    :param pymongo.MongoClient client: MongoDB client.
    :param str user_name: User login name.
    :returns: None.
    """
    now = datetime.datetime.now()
    client.shorturls.users.update_one(
        {"_id": user_name}, {"$set": {"last_login": now}}
    )
```

#### Frontend

Our URL shortening service has a web application frontend. We will use
[Flask](https://flask.palletsprojects.com/en/2.2.x/), a minimalistic and
Python-based web development framework that contains all the features we need
for this project.

To create a URL alias, the user can fill the following HTML form (the rest of
the HTML page is ommitted for brevity):

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

from . import mongo

APP_URL = os.getenv("APP_URL")
TTL_TO_HOURS = {
    "1h": 1,
    "1d": 24,
    "1w": 24 * 7,
    "1m": 24 * 30,
    "1y": 24 * 365,
}

mongo_client = mongo.Client()


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
                if mongo_client.get_url(alias) is not None:
                    msg = f"Error: alias '{alias}' already exists"
            else:
                alias_host = os.getenv("ALIAS_SERVICE_HOST")
                alias_port = os.getenv("ALIAS_SERVICE_PORT")
                alias = requests.get(
                    f"http://{alias_host}:{alias_port}/get-alias"
                ).json()["alias"]

            if msg is None:
                mongo_client.create_url(alias, long_url, username, ttl)
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
redirect the user to it (other lines of code are ommitted for brevity):

```python
# imports are ommitted

def create_app():
    # code ommitted

    @app.route("/<alias>")
    def alias(alias):
        original_url = mongo_client.get_url(alias)
        if original_url is None:
            abort(404)
        return redirect(original_url)

    return app
```

The code simply retrieves the alias from the database and redirects the user to
it, or returns a 404 error if the alias does not exist.
