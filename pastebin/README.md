# Pastebin

## 1. Requirements

### 1.1. Functional requirements

Pastebin is a text storage and sharing web application.

Users can store texts, which are then accessible at a specific URL, and
share the URL publicly.

Texts have an adjustable expiration date after which they are deleted from the
website.

Users can signup and authenticated or store text anonymously as unauthenticated
"guests".

Users have quotas, they cannot store more than a certain number of texts per
time interval.

### 1.2. Non-functional requirements

The application should be highly available.

Availability is more important that consistency: if a group of users does not
see an update for a short period of time, it's acceptable.

Data storage durability is crucial: text uploaded by users should never be
lost.

## 2. Capacity estimations

In this section we are interested in orders of magnitude and will use power of
tens instead of exact numbers. We will put references when possible.

We will accommodate 10^8 registered users, and we expect 10^7 daily active
users

A text is 10^5 bytes on average (limited to 512 KB or 64,000 ASCII
characters).

There are 10^6 text writes per day (10^1 text writes per second, 10^8 text
writes per year), and 10^7 text reads per day (10^2 text reads per second).

Write traffic is 10^6 bytes per second on average (10^11 bytes per day). Read
traffic is 10^7 bytes per second on average (10^12 bytes per day).

Texts will be stored for up to one year, so we may store up to 10^8 texts,
totalizing 10^13 bytes (10 TB) of texts.

These estimations are consistent with capacities referenced on
[TechCrunch](https://techcrunch.com/2015/12/16/pastebin-the-text-sharing-website-updates-with-an-emphasis-on-code/).

## 3. Interface

The following functions compose the application programming interface.

`put_text` stores a text and has the following parameters:
* text_id (string): Text identifier.
* text_body (string): Text to store.
* user_id (string): User identifier.
* user_ip (string): User IP address (to identify unauthenticated users).
* ttl (string): Time to live, i.e. time interval between text creation and
  expiration.
* Returns: nothing.

`get_text` retrieves a text from storage:
* text_id (string): Text identifier.
* Returns: text (string).

`delete_text` deletes a text:
* text_id (string): Text identifier.
* Returns: nothing.

`create_user` registers a new user with the application:
* user_id (string): User identifier.
* first_name (string): First name.
* last_name (string): Last name.
* password (string): Password.
* Returns: nothing.

`get_texts_by_user` retrieves the information about the texts stored by a
specific user, to display in his profile:
* user_id (string): User identifier.
* Returns: list of text_id, creation_timestamp, expiration_timestamp.

## 4. Data model

We need to store information about users and stored texts. Texts will be stored
in a distributed filesystem for durability, and their metadata will be stored
in a database. Storing the text in an object store will allow to ease traffic
on the database and keep the metadata database size low.

The table `users` has the following columns:

* user_id (string, primary key): User identifier.
* first_name (string): First name.
* last_name (string): Last name.
* joined_on (timestamp): When the user registered.
* last_connection (timestamp): The last time the user connected.

The table `texts` has the following columns:

* text_id (string, primary key): Text identifier.
* text_path (string): Path to the text object in the filesystem.
* user_id (string): User identifier of the text creator.
* user_ip (string): IP of the text creator.
* creation (timestamp): Timestamp when the text was stored.
* expiration (timestamp): Timestamp after which the text should be deleted.
* to_be_deleted (boolean): Whether a text is marked for deletion.
* deletion (timestamp): Timestamp when the texts is deleted, after expiration.

To facilitate text deletion, we add the column `to_be_deleted` that allows
marking the text for deletion. This helps identifying situations when the text
deletion process failed and needs to be retried (discussed in a later section).

## 5. High-level design

### 5.1. Application workflow

When a user stores a text, a unique identifier is assigned to the text. This
will serve to identify the text metadata in the database and in object storage.
The application verifies that users quotas are not exceeded.  Text body is
stored in a distributed file system and text metadata (who created, when it was
created, when it expires) in the database.

When a user requests an existing text, he uses the text identifier. The
corresponding text is retrieve from storage and presented to the user.

Authenticated users can see the list of texts they previously stored. An option
to delete a text is provided, in which case the text is deleted from storage
and marked as deleted in the metadata database.

### 5.2. User quotas and text limitations

Unauthenticated users will be allowed to store 10 texts per day, while
authenticated users will be allowed 100 texts per day. We could have a paid
subscription with increased user quotas.

A text is a string of characters and can be up to 512 KB, corresponding to
64,000 ASCII characters (each taking 8 bytes to store in memory).

### 5.3 Infrastructure components

#### 5.3.1. Web application server

Application servers process client requests and display stored text to users.
For redundancy and to facilitate updates we should have at least two servers. A
load balancer could process client requests and send them to application
servers based on server health.

#### 5.3.2 Metadata database

We store metadata in two tables, `users` and `texts`. These will keep track of
user activities, as well as what texts have been stored, by who, and when we
should expire them. This use-case fits an online transactional processing
(OLTP) workload, where the application runs a lot of queries that insert or
update one or few rows.

With 10^8 users, the users table would contain 10^8 records. Assuming a record
size of 10^2 bytes, the table would store 10^10 bytes (10 GB).

With 10^8 stored texts, the texts table would contain 10^8 records. Assuming a
record size of 10^2 bytes, the table would store 10^10 bytes (10 GB).

Users and texts tables totalize 10^10 bytes (tens of GB), a modest size for a
database. In terms of throughput, we expect a few hundreds of requests per
second (mostly reads).

A relational database such as PostgreSQL would fulfill our requirements.

#### 5.3.3. Text storage

We expect to store tens of terabytes of text data. This is a lot of
unstructured data, which would not fit in a simple relational database setup.
A distributed database such as a key-value store would be a viable option but
would provide many more options than necessary. Our primary goal is to store
lots of unstructured data with high durability and availability, so a
distributed filesystem is a good option. We choose
[AWS S3](https://aws.amazon.com/s3/) as our text storage system.

#### 5.3.4. Caching

Most of the traffic will be reads, so we could cache texts in memory for faster
retrieval. Cache eviction can simply follow a least-recently used policy. Cache
invalidation is simple because our requirements do not include text updates, so
we simply delete a text from the cache when necessary.

## 6. Detailed design

### 6.1. Web application

#### 6.1.1. Software tools

There are many applications and libraries available to implement web
applications. We use [Flask](https://palletsprojects.com/p/flask/) to build our
application, [Gunicorn](https://gunicorn.org/) as a WSGI server, and
[NGINX](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/) as
a reverse proxy to HTTP requests.

While Flask has a built-in WSGI server using
[Werkzeug](https://werkzeug.palletsprojects.com/en/2.2.x/), it recommended to
run a dedicated WSGI server in [production
environments](https://werkzeug.palletsprojects.com/en/2.2.x/deployment/) (in
this case Werkzeug is used as a WSGI application).

#### 6.1.2. Frontend

##### 6.1.2.1. Store a text

To store a text, users are given a
[form](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/form) where
they can paste text and choose an expiration. The following code is a snippet
from `src/templates/html.index`:

```html
<form method="post">
  <label for="text-body">Write or paste up to 64,000 characters</label>
  <textarea
    name="text-body"
    id="text-body"
    row="30"
    cols="100"
    maxlength=64000
    placeholder="Write text here"
    required
  ></textarea>
  <label for="ttl">Expired after</label>
  <select name="ttl" id="ttl">
    <option value="1d">1 day</option>
    <option value="1w">1 week</option>
    <option value="1m">1 month</option>
    <option value="1y">1 year</option>
  </select>
  <input type="submit" value="Store text">
</form>
```

We then process form data in Flask (snippet adapted from `src/__init__.py`):

```python
import flask import (
    Flask,
    render_template,
    session,
)

from . import api


def create_app(test_config=None):
    app = Flask(__name__)

    @app.route("/", methods=("GET", "POST"))
    def index():
        if request.method == "POST":
            user_id = session.get("user_id", "anonymous")
            user_ip = request.environ.get(
                "HTTP_X_REAL_IP", request.remote_addr
            )
            text_id = api.put_text(
                text_body=request.form["text-body"],
                user_id=user_id,
                user_ip=user_ip,
                ttl=request.form["ttl"],
            )
            msg = f"Stored text at /text/{text_id}"

            return render_template("index.html", message=msg)

    return app
```

Because Flask is running under NGINX, we get the user IP address with
`HTTP_X_REAL_IP`, as explained
[here](https://stackoverflow.com/questions/3759981/get-ip-address-of-visitors-using-flask-for-python).

The function `put_text` abstracts the details about text storage and metadata
(snippet from `src/api.py`):

```python
import uuid
from datetime import datetime, timedelta

from . import database
from . import object_store

def put_text(text_body, user_id, user_ip, ttl):
    creation_timestamp = datetime.now()
    ttl_hours = {
        "1h": 1,
        "1d": 24,
        "1w": 24 * 7,
        "1m": 24 * 30,
        "1y": 24 * 365,
    }[ttl]
    expiration_timestamp = creation_timestamp + timedelta(hours=ttl_hours)
    text_id = str(uuid.uuid4())
    object_store.put_text(text_id, text_body)
    database.put_text_metadata(
        text_id,
        user_id,
        user_ip,
        creation_timestamp,
        expiration_timestamp,
    )
    return text_id
```

Text IDs are generated using
[RFC 4122](https://datatracker.ietf.org/doc/html/rfc4122.html) universally
unique identifiers (UUID), so we can ensure their uniqueness.

We store the text body using the function `put_text` from the module
`object_store`, then save text metadata using the function `put_text_metadata`
from the `database` module. The `object_store` and `database` modules will be
covered in a later section.

##### 6.1.2.2. Read a text

Texts are simply displayed in an HTML [code
tag](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/code) (snippet
of `src/templates/text.html`):

```html
<body>
  <pre>
    <code>{{ text_body }}</code>
  </pre>
</body>
```

The Flask function to build the text page is simple (snippet adapted from
`src/__init__.py`):

```python
import flask import (
    Flask,
    render_template,
    session,
)

from . import api


def create_app(test_config=None):
    app = Flask(__name__)

    @app.route("/text/<text_id>")
    def get_text(text_id):
        text_body = api.get_text(text_id)
        if text_body is None:
            abort(404)
        return render_template("text.html", text_body=text_body)

    return app
```


The function `api.get_text` deals with retrieving texts. If it returns `None`,
this means the text ID does not exist and we return a 404 error (not found).
Otherwise we return the text. The following snippet is from `src/api.py`:

```python
from . import cache
from . import object_store


def get_text(text_id):
    text_body = cache.get(CACHE_TEXT_KEY.format(text_id=text_id))
    if text_body is not None:
        return text_body
    text_body = object_store.get_text(text_id)
    cache.put(CACHE_TEXT_KEY.format(text_id=text_id), text_body)
    return text_body
```

First, we try to obtain a text from cache. In case of a cache miss, we get the
text from the object store and cache results before returning them to the user.

#### 6.1.2.3 Delete a text

Users can delete a text they previously stored by sending a post request and
including the text ID in the request body. The following snippet is adapted
from `src/__init__.py`:

```python
from datetime import datetime

import flask import (
    Flask,
    render_template,
    session,
)

from . import api


def create_app(test_config=None):
    app = Flask(__name__)

    @app.route("/delete-text", methods=("POST",))
    def delete_text():
        text_id = request.form["text-id"]
        user_id, user_ip = database.get_user_by_text(text_id)
        logged_user = session.get("user_id")
        if logged_user is None or user_id != logged_user:
            abort(403)
        api.delete_text(text_id=text_id, deletion_timestamp=datetime.now())
        return "OK"

    return app
```

If the request comes from an anonymous user, we abort the request with a 403
HTTP status code (not authorized). If the user is logged in but the user ID
does not match the text creator, we abort with a 403 code as well. Otherwise,
we delete the text from object storage, metadata database, and cache. The
function `api.delete_text` is implemented as:

```python
from . import cache
from . import database
from . import object_store


def delete_text(text_id, deletion_timestamp):
    database.mark_text_for_deletion(text_id)
    object_store.delete_text(text_id)
    database.mark_text_deleted(text_id, deletion_timestamp)
    cache.delete(f"text:{text_id}")
```

We first mark the text for deletion with the SQL query:

```sql
UPDATE texts set to_be_delete = true WHERE text_id = %s;
```

This saves the delete action from the user in the database in case there is any
error during actual deletion, and the text will eventually be deleted from text
storage during the cleanup process (see the section about text storage). Once
the text is deleted from object storage, we record the deletion in the metadata
database using a timestamp. Finally we delete the text from cache.

```python
def delete_text(text_id, deletion_timestamp):
    # Mark for deletion in metadata database before deleting from object
    # storage to avoid errors when text ID shows up in web app but then is not
    # found.
    database.mark_text_for_deletion(text_id)
    object_store.delete_text(text_id)
    database.mark_text_deleted(text_id, deletion_timestamp)
    cache.delete(CACHE_TEXT_KEY.format(text_id=text_id))
```

#### 6.1.3. NGINX configuration

To keep data transfer volumes and costs as low as possible, NGINX should be
configured to send
[compressed responses](http://nginx.org/en/docs/http/ngx_http_gzip_module.html).
We use the following NGINX configuration:

```
gzip on;
gzip_disable "msie6";
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_buffers 32 4k;
gzip_http_version 1.1;
gzip_min_length 256;
gzip_types
  text/plain
  text/css
  application/json
  application/javascript
  text/xml
  application/xml
  application/xml+rss
  text/javascript;
```

The parameter `gzip_buffers` sets the number and size of buffers used to
compress a response. Our memory page size is 4 KiB, determined by running
`getconf PAGESIZE` in the console, and we use the default number of buffers.

The parameter `gzip_min_length` sets the minimum length of a response that will
be compressed. We set this to 256 bytes to only send very small uncompressed
responses.

#### 6.1.4. Infrastructure and costs

The web application will be installed on two [EC2](https://aws.amazon.com/ec2/)
instances. We choose t3.large instances with 2 vCPU and 8 GiB of memory. Our
application has no significant disk operations, a 50 GiB gp3 SSD is enough.

Application EC2 instances will be placed in a target group behind an
[application load balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html).
The target group is an [autoscaling](https://aws.amazon.com/autoscaling/) group
that maintains two web application EC2 instances at all times. This increases
the availability of application: if a server becomes unavailable, a new server
will be provisioned and ready to serve requests in a few minutes. This also
allows "rolling" application updates: we manually terminate a server and the
autoscaling group will automatically provision a new updated server.

Costs are dominated by data transfers to the Internet and by EC2 instance
costs. EC2 instances cost $1,000 (reserved instances with full upfront
payment). NGINX is configured to send compressed response data, outgoing data
volume are divided by 3 compared to uncompressed capacity estimations (we send
mostly text data, which compresses very well), bringing data transfer costs to
$10,000. Total cost would then be $11,000. The application load balancer will
cost $400 per year. Autoscaling has no additional charge.

### 6.2. Metadata database

Our metadata database engine is PostgreSQL. For durability, we will
synchronously replicate the database to a standby database server. This will
allow us to quickly recover the application if the main server becomes
unavailable, at the cost of slower writes.

#### 6.2.1. Database interface code

All functions of the `database` module are alike, they run a SQL query that
performs a specific step of the application workflow. For example, the function
`put_text_metadata` saves text information when a user stores a text:

```python
from . import sql_queries
from .config import config

import psycopg2

DB_CONFIG = {
    "host": config["database"]["host"],
    "port": config["database"]["port"],
    "dbname": config["database"]["database"],
    "user": config["database"]["user"],
    "password": config["database"]["password"],
}


def put_text_metadata(
    text_id, user_id, user_ip, creation_timestamp, expiration_timestamp,
):
    with psycopg2.connect(**DB_CONFIG) as con:
        with con.cursor() as cur:
            cur.execute(
                sql_queries.INSERT_TEXT,
                (
                    text_id,
                    f"{config['text_storage']['s3_bucket']}/{text_id}",
                    user_id,
                    user_ip,
                    creation_timestamp,
                    expiration_timestamp,
                ),
            )
```

We store SQL queries in a separate module to help with code readability, as SQL
queries have a tendency to spread over many lines and break the reader flow.
The query `sql_queries.INSERT_TEXT` is written as:

```
INSERT INTO texts (text_id, text_path, user_id, user_ip, creation, expiration)
VALUES (%s, %s, %s, %s, %s, %s);
```

We use the string placeholders `%s` to safely pass query parameters to the
`execute()` method. This is especially important when query parameters are
provided by application users, to avoid SQL injection.

#### 6.2.1. Text storage quotas

To enforce quotas, we need to keep track of how many texts were stored by
users. Authenticated users are identified by their user ID, and unauthenticated
users are identified by their IP address because they all share the user ID
'anonymous'. To count how many texts were created, we have two options: (1) we
store a counter for each user that we increment for each text created, (2) we
count how many texts were created by the user in the day that precedes the
request. Option 1 consumes less database resources at the cost of a more
complex application because we need to store the last time the counter was
reset, and periodically reset the counter. Option 2 consumes more database
resources because it runs an aggregation query but does not require an
additional counter and timestamp, only a simple aggregation query:

```
SELECT COUNT(*) AS quota FROM texts
WHERE user_id = %s AND creation > NOW() - INTERVAL '1 day';
```

We can improve the query performance by creating indexes on the texts table on
the columns `user_id`, `user_ip`, and `creation`.

The integrity of the users table is enforced by a primary key on `user_id`. If
a primary key violation happens when a new user register with our application,
we signal to the user that the user ID is already taken and prompt him to
choose another user ID.

The integrity of the texts table is enforced by a primary key on `text_id` and
a foreign key on user ID that references the primary key of the users table.
Given that we will need up to 10^8 text IDs and that there are 10^38 UUIDs
available (a UUID is 128 bits), we will ignore the very unlikely event of text
ID collision.

#### 6.2.2. Infrastructure and costs

[AWS RDS](https://aws.amazon.com/rds/) supports PostgreSQL and has a feature
named [Multi-AZ](https://aws.amazon.com/rds/features/multi-az/) that allows
synchronous data replication on a secondary server in a different availability
zone (same geographical area but different data center).

Yearly costs for our metadata database will be around $8,200 with the following
features:
- 1 db.t3.2xlarge (8 vCPU, 32 GiB memory) RDS PostgreSQL instance.
- 1 Multi-AZ replica with the same specifications as the primary instance.
- 100 GB of gp3 SSD storage on each instance.
- 100 GB of monthly backup storage.
- RDS Proxy (connection pool).
- Instances reserved for 1 year with full upfront payment of $6,760 then $120
  monthly payments for storage and proxy costs.

### 6.3. Text storage

We estimated our storage needs in the range of tens of terabytes per year (see
capacity estimations for more details). 

[Bucket versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
is used to guard against accidental deletions. The
[lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
of objects will be configured to keep a single non-current object version for
7 days before it is permanently deleted.

#### 6.3.1. Object store interface code

Code that interacts with AWS S3 is in the module `object_storage`. The function
`put_text` stores a text in S3:

```python
import zlib

import boto3

from .config import config

S3_CLIENT = boto3.client("s3")
S3_BUCKET = config["text_storage"]["s3_bucket"]
TEXT_ENCODING = config["text_storage"]["encoding"]


def put_text(text_id, text_body):
    S3_CLIENT.put_object(
        Body=zlib.compress(
            text_body.encode()
        ),
        Bucket=S3_BUCKET,
        Key=text_id,
    )
```

We use the
[boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
library to make AWS S3 requests. The
[zlib module](https://docs.python.org/3/library/zlib.html) from the Python
standard library is used to compress data before it is stored, which saves
transfer time, bandwith, and storage costs.

#### 6.3.2. Storage cleanup

When users store text, they choose a time interval after which the text expires
and is not available for reading anymore. We need a mechanism that deletes
expired texts from storage. This is necessary to keep text storage simple to
monitor, and avoid incurring unnecessary storage costs. Text deletion is
carried out by a 'cleanup' process that performs the following steps:

1. Scan the texts table in the metadata database and select the path for texts
  that are not deleted yet (column `deletion` is NULL), and where the value of
  `expiration` is smaller than the current timestamp.
2. Delete all S3 objects corresponding to the paths collected in step 1.
3. Mark the text as deleted in the metadata database by setting the current
   timestamp as a value for the column `deletion`.

It is not critical that steps 2 and 3 are atomic (succeed or fail together) so
we can keep the cleanup process simple and simply retry it in case of failure.
If an expired object is not found during step 2, we can simply skip this step
and carry on with step 3. Cleanup is performed daily at a time when load on the
system is low.

#### 6.3.2. Infrastructure costs

If we use the S3 Standard storage class to store uncompressed data,
[costs](https://aws.amazon.com/s3/pricing/) would amount to around $8,600
for the first year ($5,400 for storage and $3,300 for requests). There are no
data transfer costs between S3 and other services in the same region. A rough
estimation indicates that S3 Intelligent Tiering storage would not lead to
savings, with around 20% storage cost savings (if our storage splits evenly
between frequent and infrequent access), but an additional $5,850 of monitoring
costs. Compressing data, for example using the
[zlib module](https://docs.python.org/3/library/zlib.html) of the standard
Python library, lowers data transfer time and storage volume at the expense of
more work done by the application. Assuming a compression ratio of 3 for text,
we could lower storage costs down to $1,800 per year, for a total S3 cost of
$5,100 per year.

### 6.4. Caching

The largest part of data sent by the web application is made of texts stored in
object storage. We need an in-memory cache that supports high availability.
[Redis](https://redis.io/) features
[replication](https://redis.io/docs/management/replication/) and has a
stable and well-documented Python
[client library](https://github.com/redis/redis-py), so we choose it as our
caching engine.

If we cache 20% of write traffic, this would represent in the order of 10^10
bytes (10 GB) per day. This fits easily on the memory of a single server.

Texts stored and shared usually have an initial peak of popularity which then
fades out over time. A Least-Recently Used (LRU) eviction policy is suitable
for this pattern of access, as it keeps the most recent (hence popular) data
available.

When a user requests a text, we try to retrieve the text from the cache. In the
case of a cache miss, we retrieve the text from object storage and cache it.
For cache invalidation, we simply delete a piece of data from cache when it is
deleted by a user. Our application does not allow text updates besides
deletion, so we do not have to cover more complex eviction mechanisms.

We have the options of running the caching service locally on webservers, or on
separate servers. A local cache makes sense because cache requests only come
from web servers, and would offer fast caching operations because no network
traffic would be involved (except to keep cached data consistent between
servers). Drawbacks of local caching include (1) the inability to scale web and
caching applications independently, (2) the difficulty to invalidate cached
data when texts are deleted by users (there may be cached data that is
non-local to the deletion action) or by storage cleanup (the cleanup process
would be best run outside web servers, and then requests should be sent to web
servers to invalidate cached data). To solve these issues, we deploy caching on
dedicated web servers.

The following Redis configuration parameters are used:

```
maxmemory 16gb
maxmemory-policy allkeys-lru
```

#### 6.4.2. Infrastructure costs

Based on capacity estimations, we can deploy caching on memory-optimized EC2
instances with around 16 GiB of memory. AWS r4, r5, or r6 large EC2 instances
fit this requirement and cost around $1,500 per year (reserved instances with
full upfront payment).

### 6.5. Total infrastructure cost

Total costs for the first year are estimated at $26,000. The share of each AWS
service in the cost is approximately:

* EC2: $12,500, 48 % of total
* S3: $5,100, 20 % of total
* RDS: $8,200, 32 % of total

Notably, costs will scale with the success of the application. The majority of
costs are due to data transfers from our system to the Internet, to display
texts to users. Another large proportion of costs are related to text storage
and requests related to text storage. Therefore, costs will be proportional to
the amount of texts stored by users and how many times stored texts are read.

### 6.6. General code design

Our application does not need to store much state that frequently changes in
memory. To store user and session information, we use the relevant Flask
objects. All other state is store in the metadata database. For this reason,
our application does not implement its own classes. Classes are useful when an
application needs to represent objects that have a state (attributes) and
functions that modify the state (methods). Custom classes are not justified
to store permanent information such as application configuration, or
encapsulate a group of related functions.

Our application code encapsulates functions in modules, offering the same
syntax for import and calls as a custom class. Configuration is available to
all functions by storing it in global variables.
