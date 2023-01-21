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

A paste is 10^5 bytes on average (limited to 512 KB).

There are 10^6 text writes per day (10^1 text writes per second, 10^8
text writes per year), and 10^7 text reads per day (10^2 text reads per
second).

Write traffic is 10^6 bytes per second on average (10^11 bytes per day). Read
traffic is 10^7 bytes per second on average (10^12 bytes per day).

Pastes will be stored for up to 5 years, so we may store up to 5 x 10^8 texts,
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
* joined_date (date)
* last_connection_date (date)

With 10^8 users, the table would contain 10^8 records. Assuming a record size
of 10^2 bytes, the table would store 10^10 bytes (10 GB). An index on user_id
would increase stored data by 20 % (1 column out of 5), for a total of 12 GB.

The table 'texts' has the following columns:

* text_id (string, primary key): unique text identifier
* text_path (string): path to the text object in the object store
* user_id (string): user identifier of the text creator
* user_ip (string): IP of the text creator
* creation_date (date): date when the text was stored
* expiration_date (date): date after which the text should be deleted

We anticipate that we will enforce user quotas by querying the 'texts' table,
and count how many texts were recently stored. This means that we will need
indexes on user_id, user_ip (for unauthenticated users), and creation_date, in
order to have a reasonable query performance.

With 5 x 10^8 stored texts, the table would contain 5 x 10^8 records. Assuming
a record size of 10^2 bytes, the table would store 5 x 10^10 bytes (50 GB).
Indexes will probably increase storage by around 70 % (4 columns out of 6), for
a total storage size of 85 GB.

The 'users' and 'texts' tables totalize around 100 GB, a modest size for a
database. Given that we expect a few hundreds of requests per second (mostly
reads), a relational database such as PostgreSQL or MySQL would fulfill our
requirements.

## High-level design

### Application workflow

When a user stores a text, a unique text identifier is assigned to the text to
serve as a URL for the text. The text is stored in an object store, such as AWS
S3. Text metadata is stored in the metadata database. As described in the
data model section, we will use a relational database for the metadata
database.

When a user requests an existing text, he uses the text identifier. The
corresponding text is retrieve from the object store and presented to the user.

### User quotas and text limitations

Unauthenticated users will be allowed to store 10 texts per day, while
authenticated users will be allowed 100 texts per day. We could have a paid
subscription with increased user quotas.

A text is a string of UTF-8 characters and can be up to 512 KB.

### Infrastructure components

Application servers process client requests and display stored text to users.
For redundancy and to facilitate updates we should have at least two servers. A
load balancer could process client requests and send them to application
servers using a round-robin mechanism. AWS EC2 instances with ELB would provide
these features.

The metadata database is stored in a relational engine: PostgreSQL. We have two
database servers with one serving as a synchronous replica, for data
durability. The asynchronous replica should be stored in a different data
center. AWS RDS with multi-AZ would provide all these features.

For text storage, an object store such as AWS S3 would be suitable. We would
use the standard storage class to start with. It may be beneficial to use the
Intelligent Tiering storage class, which adapts the data access tier
automatically based on access frequency. However, objects smaller than 128 KB
will be always charged like they are 128KB, so we would analyze the size
distribution of actually stored objects before making a decision. To guard
against accidental object deletion, bucket versioning should be enabled.
Deleted objects will be retained for 7 days as a non-current object version
before being permanently deleted, thanks to a lifecycle policy.

Most of the traffic will be reads, so we could cache texts in memory for faster
retrieval. If we cache 20% of write traffic, this would represent in the order
of 10^10 bytes (10 GB) per day. This fits easily on the memory of a single
server. Cache eviction can simply follow a least-recently used policy. Cache
invalidation can use 'write around', to process writes faster and avoid
updating the cache with a value that may not be subsequently retrieved.

## Detailed design

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
