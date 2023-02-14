# Instagram

## 1. Requirements

### 1.1. Functional

A web application displays pictures uploaded by users.

Users can share pictures publicly.

Pictures can have tags arbitrarily chosen by users.

Users can leave comments on others' pictures, and signal they like the picture.

Pictures can be organized in albums.

Users can apply filters on pictures (black and white, enhance contrast, change
dominant color, etc.).

Users can follow each other, and be informed of pictures uploaded by people
they follow.

A picture "feed" is presented to users. This feed ranks pictures by decreasing
importance, based on whether the picture is from somebody they follow, picture
popularity, etc.

### 1.2. Non-functional

The application must be highly available.

The application must be eventually consistent, with different users seeing the
same public contents with a short lag (a few seconds at most). Consistency is
less important than availability.

Data must be store with high durability, uploaded pictures should not be lost.

## 2. Capacity estimations

A picture is 10^6 bytes on average to upload, 10^5 to download (because it is
stored downsized).

There are 10^8 daily active users.

There are 10^0 pictures uploaded per user per day, or 10^8 pictures uploaded
per day (10^3 per second). The data volume is 10^14 bytes (100TB) per day, or
10^9 bytes (1GB) per second.

There are 10^1 pictures seen per user per day, or 10^9 pictures seen per day
(10^4 per second). The data volume is 10^14 bytes (100TB) per day, or 10^9
bytes (1GB) per second.

Pictures will be compressed before storage, to a ratio of approximately 10:1.
Compressed picture storage will amount to 10^15 bytes (1PB) after a year.

## 3. Data model and queries

Capacity estimations suggest that image information represents a very high
volume of data. With an average of 10^9 images uploaded every day, and assuming
an average record size of 10^2 bytes in a table that would store image
information, this table alone would represent around 10^13 bytes (10TB) after
one year. On top of this, we estimage the database should support 10^4 (tens of
thousands) of queries per second. These requirements pushe the limits of what a
relational database can handle. We need a distributed database that supports
sharding and a high query throughput. Apache Cassandra is a reasonable choice.

It is difficult to design a data model to store in a database such as Cassandra
without first determining the most important query patterns. We first build a
conceptual data model, then define application queries. Then, we build the
logical (table structure) and physical (data types) data model. Finally, we
build the database schema.

### Conceptual data model

#### Objects

In this section we describe the most important objects our application
represents, their attributes, and their relationships.

A **user** has the following attributes:

* user identifier
* first name
* last name
* password
* registration timestamp

Users establish **connections** to the application, which have the attributes:

* user identifier
* user IP address
* timestamp
* success or failure

Users publish **images**:

* image identifier
* image owner identifier
* image description
* image path to where data is stored
* publication timestamp
* deletion timestamp (eventually)

Images have **tags**:

* tag name
* image identifier

Images have **comments**:

* image identifier
* comment text
* user identifier
* comment creation timestamp
* comment deletion timestamp (eventually)

Images have **likes**:

* image identifier
* user identifier
* like creation timestamp
* like deletion timestamp (eventually)

Users create **albums** to store images:

* album name
* user identifier
* album creation timestamp
* album deletion timestamp (eventually)

#### Relationships

User <-1-n-> Connection

User <-1-n-> Image

User <-1-n-> Album

Image <-n-m-> Tag

Image <-1-n-> Comment

User <-1-n-> Comment

Image <-1-n-> Like

User <-1-n-> Like

Album <-1-n-> Image

User <-n-m-> User

### Queries

#### Write queries

The application supports the following write queries from users:

* Query 1: Publish an image.

* Query 2: Tag an image.

* Query 3: Create an album.

* Query 4: Add an image into an album.

* Query 5: Comment an image.

* Query 6: Like an image.

* Query 7: Follow a user.

#### Read queries

When a user logs in, he is presented with a recent activity of other users.
Recent activity from followed users is presented first. We need to support the
following queries:

* Query 1: What are the images published by users I follow?

After queries 1, a user may choose to see the details of an image:

* Query 2: What are the details of an image (publication date, tags, etc.)?
* Query 3: What are the comments of an image?
* Query 4: What are the likes of an image?

A user could also be interested in the activities of a specific user:

* Query 5: What information is available about this user?
* Query 6: What images were published by this user?
* Query 7: What are the albums created by this user?
* Query 8: What images are displayed in this album?
* Query 9: Who is following me?

#### Application workflow

The queries can be displayed in the context of the application workflow. Read
queries are represented by 'RQ' and write queries by 'WQ'.

RQ1 -> View user images -> RQ3,RQ4 -> View image details -> WQ2,WQ4,WQ5,WQ6,RQ5

RQ5 -> View user details -> RQ6 -> View user images
                         -> RQ7 -> View user albums -> WQ4,RQ8 -> View user images
                         -> WQ7
                         -> RQ9,RQ10

WQ1 -> View user images

WQ3 -> View user albums

### Logical and physical data model

In this section we determine what database tables we will use to support the
application queries, as well as how data is partitioned and clustered within a
partition. There are two important considerations to keep in mind: a query
should necessitate a small number of partitions (ideally one), and each row
should have a unique key (possibly by using a combination of partition and
clustering keys).

In each table, we present column names, keys, and data types. We store all
tables under a single keyspace.

For each table we will estimate the partition size defined as:

```math
N_v = N_r ( N_c - N_{pk} - N_s ) + N_s
```

With `Nv` the number of values in the partition, `Ns` the number of static
columns, `Nr` the number of rows, `Nc` the number of columns and `Npk` the
number of primary key columns. Because our capacity estimations use powers of
ten and that all tables have less than 10 columns, we consider that `Nv` is
equivalent to `Nr`.

The size on disk of partitions is calculated with the following formulat:

```math
S_t = \sum_{i}sizeOf(c_k_i) + \sum_{j}sizeOf(c_s_j) + N_r \times
\big(\sum_{k}sizeOf(c_r_k) + \sum_{l}sizeOf(c_c_l)]\big) + N_v \times
sizeOf(t_{avg})
```

Read queries 1 is satisfied by the tables `user_follows` and `images_by_user`.

Table `user_follows`:

* `follower_id` (partition key): text
* `followed_id`: text
* `creation_timestamp`: timestamp

The partition size of `user_follows` depends on how many people a user follows,
and is estimated to be 10^2 on average.

Table `images_by_user`:

* `owner_id` (partition key): text
* `publication_timestamp` (clustering key): timestamp
* `image_id`: uuid
* `image_path`: text

The partition size is proportional to the number of images owned by users, on
average. After a year, a user has uploaded 10^2 images, so the average
partition size is 10^2.

Read query 2 is satisfied by the table `images.

Table `images`:

* `image_id` (partition key): UUID
* `image_path`: TEXT
* `publication_timestamp`: TIMESTAMP
* `description`: text
* `album_name`: text
* `tags`: set(text)

The value of `image_id` is unique, so the partition size for this table is one.

Read queries 3 and 4 are satisfied by two tables: `image_comments` and
`image_likes`. Each table is partitioned by image identifier because this query
is interested in a specific image. To ensure primary key uniqueness, we add a
timestamp and user identifiers as clustering keys.

Table `image_comments`:

* `image_id` (partition key): uuid
* `creation_timestamp` (clustering key): timestamp
* `user_id` (clustering key): text
* `comment_text`: text

Table `image_likes`:

* `image_id` (partition key): uuid
* `user_id` (clustering key): text
* `creation_timestamp`: timestamp

Assuming an average of 10^1 comments and likes per image, the partition size
for both `image_comments` and `image_likes` tables is 10^1 on average.

Read queries 5, 6, and 7 are satisfied by the `users` table, partitioned by
user identifier (we are interested in a single user, and they are unique).

Table `users`:

* `user_id` (partition key): text
* `registration_timestamp`: timestamp
* `first_name`: text
* `last_name`: text
* `password`: text
* `album_names`: set<text>

Each user identifier is unique, so the partition size for `users` is 1.

Read query 8 is satisfied by the table `albums`, partitioned by album name
and album owner identifier (an album name is not unique by itself).

Table `albums`:

* `album_name` (partition key): text
* `owner_id` (clustering key): text
* `creation_timestamp`: timestamp
* `image_ids`: set<uuid>

Read query 9 is satisfied by the table `user_is_followed`, which is an inverted
version of the table `user_follows` we saw previously:

Table `user_is_followed`:

* `followed_id` (partition key): text
* `follower_id`: text
* `creation_timestamp`: timestamp

The partition size of `user_is_followed` depends on how many people follow this
user. Popular users could have millions of followers, leading to very
imbalanced partition sizes.

### What about a graph model?

The data model is complicated because it has to model several
many-to-many relationships. A graph model can easily represent such
relationship, which not only simplifies the schema but the queries as well.

The graph model contains nodes for the following objects (for the list of
attributes, see the relational model):

* users
* user connections
* images
* albums

Image filters and tags are attributes of image nodes.

The graph contains the following edges (relationships):

* connects (from users to connections)
* creates image (from users to images)
* creates album (from users to albums)
* can see album (from users to albums)
* follows (from users to users)
* comments (from users to images)
* likes (from users to images)

An issue with the graph model is how inflexible it is with sharding. To
avoid joining data across shards and maintain good query performance, each
shard should contain a partition of the full graph that is independent of other
partitions. There is no straighforward way to achieve this in our data model.

## 5. High-level design

### System components

Web application servers runs the user-facing server and processes users
requests: image upload, organization into albums, browsing images of other
users, browsing the user image feed, etc.

A load balancer may be placed between clients and the application web servers,
to distribute traffic, protect web servers, and perform SSL termination.

Images are stored on a distributed filesystem, ensuring high availability and
durability.

Application data and image metadata is stored on a database. The database
engine needs to fulfill the following requirements:

* Run on a cluster of machines and support sharding and replication, because
  the application needs to store tens of terabytes of (non-image) data.
* Support secondary indexes to facilitate some queries (e.g. get all images
  owned by a given user).
* Have good performance to quickly return results to the web application.
* Availability of a Python client, to fit in our web application.

A database application such as MongoDB, DynamoDB, or Apache Cassandra would be
a good fit.

The application will be read heavy, so caching a cache layer to store image
data would improve application performance.

### Image upload

Users upload images through a web application. Images can have an arbitrary
title (up to a 50 characters) and tags (up to 10 tags, 20 characters each).

### Image storage

Because images are unstructured data and each have a size of at least hundreds
of kilobytes, it would not be wise to store them in a traditional database:
database size would be huge (several petabytes, see capacity estimations) and
database traffic as well.

Images are stored on a distributed filesystem to ensure high durability and
facilitate storage management.

Images are assigned a UUID before storage. After storage, the image UUID is
used as a key for retrieval.

Image metadata (owner, upload timestamp, title, tags, etc.) are stored in a
metadata database that supports richer queries.

Before storage, images are resized to a maximum width of 1080 pixels if they
exceed this width. Images are compressed to save storage costs and network
bandwidth. Also, an image thumbnail is generated and stored on the distributed
filesystem as well, to dress application icons.

### Caching

If we cache 20% of daily image traffic, it represents around 10^13 bytes (10T
) of data. Storing this amount of information would require at least a few tens
of servers, as cloud providers offer servers with each several terabytes of
memory.

Assuming the popularity of most images will fade away with time, a
least-recently used cache expiration policy is a reasonable choice.

The application does not support image updates, so we do not need to specify a
cache invalidation policy.

## 6. Detailed design
