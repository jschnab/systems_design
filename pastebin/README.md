# Pastebin

## Requirements

### Functional requirements

Pastebin is a text storage and sharing web application.

Users can store short texts, which is then accessible at a specific URL, and
share the URL publicly or with a group of contacts.

Texts have an adjustable expiration date after which they are deleted from the
website.

Users can signup and authenticated or store text anonymously as unauthenticated
"guests".

Users have quotas, they cannot store more than a certain number of texts per
time interval.

### Non-functional requirements

The application should be highly available, basically always reachable.

Availability is more important that consistency: if a group of users does not
see an update for a short period of time, it's acceptable.

Data storage durability is crucial: text uploaded by users should never be
lost.

## Capacity estimations

We will accommodate 10^8 registered users, and we expect 10^7 daily active
users.

A paste is 10^5 bytes on average (limited to 512 KB or 64,000 ASCII
characters).

There are 10^6 text writes per day (10^1 text writes per second, 10^8
text writes per year), and 10^7 text reads per day (10^2 text reads per
second).

Write traffic is 10^6 bytes per second on average (10^11 bytes per day). Read
traffic is 10^7 bytes per second on average (10^12 bytes per day).

Texts will be stored for up to 5 years, so we may store up to 5 x 10^8 texts,
totalizing 5 x 10^13 bytes (50 TB) of texts.

## Interface

The following functions compose the application programming interface (all
functions have the user ID as a parameter, so it is ommitted):

* store_text(
    text_id,
    text_body,
    user_id,
    user_ip,
    creation_timestamp,
    expiration_timestamp
  ): Stores a text entered by a user, with a given expiration timestamp.
  Because some users are not authenticated (anonymous), we also store the IP
  address of the request to limit the number of requests we serve.

* retrieve_text(text_id): Returns a text that was previously stored.

* delete_text(text_id): Permanently deletes a text.

* create_user(user_id, first_name, last_name, password, creation_timestamp):
  Registers a new user in the database.

* get_texts_by_user(user_id): Retrieves the information about the texts stored
  by a specific user, to display in his profile.

## Data model

We need to store information about users and stored texts. Texts will be stored
in a object store, such as AWS S3, and their metadata will be stored in a
database. Storing the text in an object store will allow to ease traffic on
the database and keep the metadata database size low.

The table 'users' has the following columns:

* user_id (string, primary key)
* first_name (string)
* last_name (string)
* joined_on (timestamp)
* last_connection (timestamp)

The table 'texts' has the following columns:

* text_id (string, primary key): unique text identifier
* text_path (string): path to the text object in the object store
* user_id (string): user identifier of the text creator
* user_ip (string): IP of the text creator
* creation (timestamp): timestamp when the text was stored
* expiration (timestamp): timestamp after which the text should be deleted
* deletion (timestamp): timestamp when the texts is deleted, after expiration

We anticipate that we will enforce user quotas by querying the 'texts' table,
and count how many texts were recently stored. This means that we will need
indexes on user_id, user_ip (for unauthenticated users), and creation_date, in
order to have a reasonable query performance.

## High-level design

### Application workflow

When a user stores a text, a unique identifier is assigned to the text. This
will serve to identify the text metadata in the database and in object storage.
The application verifies that users quotas are not exceeded (10 texts per day
for unauthenticated (anonymous) users, and 100 texts per day for authenticated
users), then stores the text body in object storage and text metadata (who
created, when it was created, when it expires) in the database.

When a user requests an existing text, he uses the text identifier. The
corresponding text is retrieve from object store and presented to the user.

Authenticated users can see the list of texts they previously stored. An option
to delete a text is provided, in which case the text is deleted from object
storage, and marked as deleted in the metadata database.

### User quotas and text limitations

Unauthenticated users will be allowed to store 10 texts per day, while
authenticated users will be allowed 100 texts per day. We could have a paid
subscription with increased user quotas.

A text is a string of characters and can be up to 512 KB.

### Infrastructure components

#### Web application server

Application servers process client requests and display stored text to users.
For redundancy and to facilitate updates we should have at least two servers. A
load balancer could process client requests and send them to application
servers based on server health.

#### Metadata database

We store metadata in two tables, 'users' and 'texts'. These will keep track of
user activities, as well as what texts have been stored, by who, and when we
should expire them. This use-case fits an online transactional processing
(OLTP) workload.

With 10^8 users, the users table would contain 10^8 records. Assuming a record
size of 10^2 bytes, the table would store 10^10 bytes (10 GB).

With 5 x 10^8 stored texts, the texts table would contain 5 x 10^8 records.
Assuming a record size of 10^2 bytes, the table would store 5 x 10^10 bytes
(50 GB).

Users and texts tables totalize 10^10 bytes (tens of GB), a modest size for a
database. In terms of throughput, we expect a few hundreds of requests per
second (mostly reads).

In summary, a relational database such as PostgreSQL would fulfill our
requirements.

#### Text storage

We expect to store up to 50 TB of text data. This is a lot of unstructured
data, which would not fit in a simple relational database setup. A distributed
database such as a key-value store would be a viable option but would provide
many more options than necessary. Our primary goal is to store lots of
unstructured data with high durability and availability, so a distributed
filesystem (e.g. HDFS, AWS S3) is a good option.

### Caching

Most of the traffic will be reads, so we could cache texts in memory for faster
retrieval. Cache eviction can simply follow a least-recently used policy. Cache
invalidation can use 'write around', to process writes faster and avoid
updating the cache with a value that may not be subsequently retrieved.

## Detailed design

### Web application

There are many applications and libraries available to implement web
applications. We use [Flask](https://palletsprojects.com/p/flask/) to build our
application and
[NGINX](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/) as
a reverse proxy to serve client requests.

#### NGINX configuration

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
compress a response. Our memory page size is 4 KB, determined by running
`getconf PAGESIZE` in the console, and we use the recommended number 32.

The parameter `gzip_min_length` sets the minimum length of a response that will
be compressed. We set this to 256 bytes to only send very small incompressed
responses.

#### Infrastructure and costs

The web application will be installed on two [EC2](https://aws.amazon.com/ec2/)
instances. We choose t3.large instances with 2 vCPU and 8 GiB of memory. Our
application has no significant disk operations, a 50 GB gp3 SSD is enough.

Application EC2 instances will be placed in a target group behind an
[application load balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html).
The target group is an [autoscaling](https://aws.amazon.com/autoscaling/) group
that maintains two web application EC2 instances at all times. This increases
the availability of application: if a server becomes unavailable, a new server
will be provisioned and ready to serve requests in a few minutes. This also
allows "rolling" application updates: we manually terminate a server in and the
autoscaling group will automatically provision a new updated server.

Costs are dominated by data transfers to the Internet and by EC2 instance
costs. EC2 instances cost $1,000 (reserved instances with full upfront
payment). NGINX is configured to send compressed response data, outgoing data
volume are divided by 3 compared to uncompressed capacity estimations (we send
mostly text data, which compresses very well), bringing data transfer costs to
$10,000. Total cost would then be $11,000. The application load balancer will
cost $400 per year. Autoscaling has no additional charge.

### Metadata database

Our metadata database engine is PostgreSQL. For durability, we will
synchronously replicate the database on a standby database server. This will
allow us to quickly recover the application if the main server become
unavailable, at the cost of longer write durations.

To enforce quotas, we need to keep track of how many texts were stored by
users. Authenticated users are identified by their user ID, and unauthenticated
users are identified by their IP address because they all share the user ID
'anonymous'. To count how many texts were created, we have two options: (1) we
store a counter for each user that we increment for each text created, (2) we
count how many texts were created by the user in the day that precedes the
request. Option 1 consumes less database resources at the cost of a more
complex application because we need to store the last time the counter was
reset, and periodically reset the counter. Option 2 consumes more database
resources but does not require an additional counter and timestamp, only a
simple aggregation query. We can improve the query performance by creating
indexes on the texts table on the columns 'user_id', 'user_ip', and 'creation'.

The integrity of the users table is enforced by a primary key on user ID. If a
primary key violation happens when a new user register with our application, we
signal to the user that the user ID is already taken and prompt him to choose
another user ID.

The integrity of the texts table is enforced by a primary key on text ID and a
foreign key on user ID that references the primary key of the users table. Text
IDs are generated by our application using
[RFC 4122](https://datatracker.ietf.org/doc/html/rfc4122.html) universally
unique identifiers (UUID), so we can ensure their uniqueness. Given that we
will need up to 10^8 text IDs and that there are 10^38 UUIDs available (a UUID
is 128 bits), we will ignore the potential issue of a text ID collision.

#### Infrastructure and costs

[AWS RDS](https://aws.amazon.com/rds/) supports PostgreSQL and has a feature
named [Multi-AZ](https://aws.amazon.com/rds/features/multi-az/) that allows
synchronous data replication on a secondary server in a different availability
zone (same geographical area but different data center).

Yearly costs for our metadata database will be around $8,200 with the following
features:
- 1 db.t3.2xlarge (8 vCPU, 32 GiB memory) RDS PostgreSQL instance
- 1 Multi-AZ replica with the same specifications as the primary instance
- 100 GB of gp3 SSD storage on each instance
- 100 GB of monthly backup storage
- RDS Proxy (connection pool)
- instances reserved for 1 year with full upfront payment of $6,760 then $120
  monthly payments for storage and proxy costs

### Text storage

We estimated our storage needs in the range of tens of terabytes per year (see
capacity estimations for more details). 

We choose [AWS S3](https://aws.amazon.com/s3/) as our text storage system.

#### Storage cleanup

When users store text, they choose a time interval after which the text expires
and is not available for reading anymore. We need a mechanism that deletes
expired texts from storage. This is necessary to keep text storage simple to
monitor, and avoid incurring unnecessary storage costs. Text deletion is
carried out by a 'cleanup' process that performs the following steps:

1. Scan the texts table in the metadata database and select the path for texts
  that are not deleted yet (column 'deletion' is NULL), and where the value of
  'expiration' is smaller than the current timestamp.
2. Delete all S3 objects corresponding to the paths collected in step 1.
3. Mark the text as deleted in the metadata database by setting the current
   timestamp as a value for the column 'deletion'.

It is not critical that steps 2 and 3 are atomic (succeed or fail together) so
we can keep the cleanup process simple and simply retry it in case of failure.
If an expired object is not found during step 2, we can simply skip this step
and carry on with step 3. Cleanup is performed daily at a time when load on the
system is low.

[Bucket versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
is used to guard against accidental deletions. The
[lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
of objects will be configured to keep a single non-current object version for
7 days before it is permanently deleted.

If we use the S3 Standard storage class to store uncompressed data,
[costs](https://aws.amazon.com/s3/pricing/) would amount to around $8,600
for the first year ($5,400 for storage and $3,300 for requests). There are no
data transfer costs between S3 and other services in the same region. A rough
estimation indicates that S3 Intelligent Tiering storage would not lead to
savings, with around 20% storage cost savings (if our storage splits evenly
between frequent and infrequent access), but an additional $5,850 of monitoring
costs. Compressing data, for example using the
[zlib module](https://docs.python.org/3/library/zlib.html) of the standard
Python library, would lower data transfer time and storage volume at the
expense of more work done by the application. Assuming a compression ratio of 3
for text, we could lower storage costs down to $1,800 per year, for a total S3
cost of $5,100 per year.

### Caching

The largest part of data sent by the web application is made of texts stored in
object storage. We need an in-memory cache that supports high availability.
[Redis](https://redis.io/) supports
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
data when texts are deleted by users (there may cached data that is non-local
to the deletion action) or by storage cleanup (the cleanup process would be
best run outside web servers, and then requests should be sent to web servers
to invalidate cached data). To solve these issues, we deploy caching on
dedicated web servers.

The following Redis configuration parameters are used:

```
maxmemory 16gb
maxmemory-policy allkeys-lru
```

#### Infrastructure cost

Based on capacity estimations, we deploy caching on memory-optimized instances
with around 16 GB of memory. AWS r4, r5, or r6 large EC2 instances fit this
requirement and cost around $1,500 per year (reserved instances with full
upfront payment).

### Total infrastructure cost

Total costs for the first year are estimated at $26,000. The share of each AWS
service in the cost is approximately:

* EC2: $12,500, 48 % of total
* S3: $5,100, 20 % of total
* RDS: $8,200, 32 % of total

Notably, costs will scale with the success of the application. The majority of
costs are due to data transfers from our system to the Internet, to display
texts to users, and a large proportion of costs are related to text storage and
requests related to text storage. Therefore, costs will be proportional to the
amount of texts stored by users and how many times stored texts are read.

## Application code

do not use classes just to store configuration because config is a permanent
state (it does not change depending on the application activity), instead use
modules to encapsulate functions and load configuration to the global scope so
that all functions in a module can read config

when connecting to postgres, use one connection per SQL statement to simplify
transaction logic. for example, several cursors could share the same
transaction, depending on the isolation level, so it may not be immediately
clear when reading the code if a SQL statement (or a group of SQL statements)
are running in their own transaction

do not let SQL commands or other database details leak into the frontend code,
but instead wrap them in functions that are called by the frontend code

when creating a new user or a new text in the database, we enforce uniqueness
with the primary key constraint on user ID and text ID, independently of the
chosen transaction isolation level

error management: to avoid repeated and complicated exceptions management code,
we manage errors at the lowest possible level (e.g. in the s3.py module for AWS
S3 operations). we initially thought that low-level functions could return an
error message to signal an issue to higher-level code, and None to signal
success, but some functions have to return data (e.g. retrieving a text from
S3), so we have to distinguish a return value that is an error from a return
value that is data. one way to do this is to return a tuple (code, data)
where code indicates success or failure, and which kind of failure happened,
while data contains the expected data (possibly None in case of failure).
while this looks elegant in a simple application, there are three potential
issues in a complex application, (1) we need a system to organize the numerous
error codes, (2) at a high level we may replicate the complexity of low-level
error management, simply with different error labels, (3) it becomes difficult
to call error-managed functions in other error-managed functions, because the
return value or the higher-level function would become a tuple (code, data).
