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

## 3. Application programmatic interface

A user publishes a picture using the function `publish_image`:

* Parameters
    * `image_data` (bytes): Data that make up the image.
    * `image_title` (string): Image title.
    * `user_id` (string): Identifier of the user who publishes the image.
    * `tags` (list(string)): List of tags the user added to the image.
    * `album_id` (integer): Identifier of the album the images belongs to.
    * `filter_id` (integer): Identifier of the filter applied to the image.
* Returns: Image identifier (string).

An image can be retrieved using the function `get_image`:

* Parameters
    * `image_id` (string): Image identifier.
* Returns:
    * Image data (bytes).
    * User identifier (who published the image, string).
    * Tags (list(string)).

An image is deleted using the function `delete_image`:

* Parameters
   * `image_id` (string): Image identifier.
* Returns: Nothing.

An album can be created using the function `create_album`:

* Parameters:
    * `album_name` (string): Name of the album.
    * `user_id` (string): Identifier of the user who creates and owns the
      album.
    * `private` (boolean): Whether the album is private and visible only by
      users invited by the owner.
* Returns: Nothing.

An album owner can invite users to see a private album with the function
`invite_to_album`:

* Parameters:
   * `album_name` (string): Name of the album.
   * `owner_id` (string): Identifier of the user who owns the album.
   * `invitee_id` (string): Identifier of the user who is invited.
* Returns: Nothing.

An image can be moved to an album with the function `move_img`:

* Parameters
    * `image_id` (string): Image identifier.
    * `album_name` (string): Name of the album.
    * `owner_id` (string): Identifier of the user who owns the album.
* Returns: Nothing.

A filter can be applied on an image using the function `apply_img_filter`:

* Parameters:
    * `image_data` (bytes): Image data.
    * `filter_name` (string): Name of the filter.
* Returns:
    * Filtered image data (bytes).

A user can comment on a picture with the function `comment_img`:

* Parameters:
    * `image_id` (string): Image identifier.
    * `commenter_id` (string): Identifier of the user who comments.
    * `comment_body` (string): Comment text.
* Returns: Nothing.

A user can 'like' an picture through the function `like_img`:

* Parameters:
    * `image_id` (string): Image identifier.
    * `liker_id` (string): Identifier of the user who likes the image.
* Returns: Nothing.

A user can follow another user and be notified of their activities with the
function `follow_user`:

* Parameters:
    * `follower_id` (string): Identifier of the user who follows.
    * `followee_id` (string): Identifier of the user who is followed.
* Returns: Nothing.

## 4. Data model

The data model aims at supporting the fundamental operations of the
application, it is not optimized for analytics.

There are several many-to-many relationships we need to represent. We slightly
denormalize the schema and store some attributes in arrays to facilitate
representing these relationships.

Table `users`:

* `user_id` (string key): User identifier.
* `first_name` (string): First name.
* `last_name` (string): Last name.
* `password` (string): Hashed password.
* `creation_timestamp` (datetime): Date and time the user registered.
* `deletion_timestamp` (datetime): Date and time the user left.
* `albums_own` (set(integer)): Identifiers for albums owned by the user.
* `albums_access` (set(integer)): Album identifiers from other users a user
  has access to.

With 10^8 users and assuming an average record size of 10^2 bytes, the table
size is 10^10 bytes (10 GB).

Table `user_connections`:

* `user_id` (string): User identifier.
* `user_ip` (string): IP address of the user.
* `connection_timestamp` (datetime): Date and time of the connection attempt.
* `success` (boolean): Whether the connection was successful.

With 10^8 users connecting every day, assuming an average record size of 10^1
bytes, the table size is 10^11 (100GB) after a year.

Table `followers`:

* `follower_id` (string): User who follows.
* `followee_id` (string): User who is followed.
* `follow_timestamp` (datetime): When the interaction started.
* `unfollow_timestamp` (datetime): When the interaction eventually ended.

With 10^8 users each having 10^1 contacts, assuming an average record size of
10^1 bytes, the table size is 10^10 bytes (10GB).

Table `images`:

* `image_id` (uuid, primary key): Image identifier.
* `image_title` (string): Image title.
* `image_path` (string): Path of the image in the storage system.
* `owner_id` (string, references users.user_id): User identifier of the image
  owner.
* `album_id` (integer): Identifier of the album the image belongs to.
* `publication_timestamp` (datetime): Date and time the image was published.
* `deletion_timestamp` (datetime): Date and time the image was deleted.
* `to_be_deleted` (boolean): Whether the image was marked for deletion.
* `filter` (string): Name of the filter applied on the image.
* `tags` (set(text)): Tags of the image.

With an average of 10^9 images uploaded every day, assuming an average record
size of 10^2 bytes, the table size is 10^13 bytes (10TB) after a year.

The attribute `image_id` has the highest cardinality because each value is
unique, so we could shard the table by image identifier. This would spread the
images of a specific user over several storage nodes, impairing the performance
of queries that collect the images of a single user. Sharding by owner
identifier could mitigate this issue, but would create another issue: nodes
that store data for images owned by popular users would process a
disproportionately high amount of queries. Another solution would be to have a
hybrid sharding strategy: data for popular users is sharded by image identifier
and stored on table A, while data for normal users is sharded by user identifier
and stored on table B. We will use the simpler solution of sharding by image
identifier, which avoids cluster load skews due to heterogeneous user
popularity.

Table `albums`:

* `album_name` (string, primary key): Album name.
* `owner_id` (string, primary key): User who owns the album.
* `creation_timestamp` (datetime): Date and time the album was created.
* `deletion_timestamp` (datetime): Date and time the album was deleted.
* `private` (boolean): Whether the album is private or not.
* `users` (set(text)): Users who can access an album.

With 10^2 albums per user on average, assuming a record size of 10^2 bytes, the
table size is 10^12 bytes (1TB).

Table `image_comments`:

* `image_id` (uuid): Image identifier.
* `user_id` (string): Identifier of user who
  commented.
* `comment` (string): Text of the comment.
* `creation_timestamp` (datetime): When the comment was made.
* `deletion_timestamp` (datetime): When the comment was eventually deleted.

Assuming an average of 1 comment per image, and a record size of 10^2 bytes,
after a year the table size is 10^11 bytes (100GB).

Table `image_likes`:

* `image_id` (uuid): Image identifier.
* `user_id` (string): Identifier of user who
  liked the image.
* `like_timestamp` (datetime): When the 'like' was made.
* `dislike_timestamp` (datetime): When the 'like' was eventually removed.

Assuming an average of 1 'like' per image, and a record size of 10^1 bytes,
after a year the table size is 10^10 bytes (10GB).

The total size required to store the database is dominated by the table
`images`, which weighs tens of terabytes. Sharding will be required to spread
data storage on a cluster.

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
