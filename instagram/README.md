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

A picture is 10^6 bytes on average.

There are 10^8 daily active users.

There are 10^0 pictures uploaded per user per day, or 10^8 pictures uploaded
per day (10^3 per second). The data volume is 10^14 bytes (100TB) per day, or
10^9 bytes (1GB) per second.

There are 10^1 pictures seen per user per day, or 10^9 pictures seen per day
(10^4 per second). The data volume is 10^15 bytes (1PB) per day, or 10^10 bytes
(10GB) per second.

Pictures will be compressed before storage, to a ratio of approximately 10:1.
Compressed picture storage will amount to 10^15 bytes (1PB) after a year.

## 3. Application programmatic interface

A user publishes a picture using the function `publish_img`:

* Parameters
    * `image_data` (bytes): Data that make up the image.
    * `user_id` (string): Identifier of the user who publishes the image.
    * `tags` (list(string)): List of tags the user added to the image.
* Returns: Image identifier (string).

An image can be retrieved using the function `get_img`:

* Parameters
    * `image_id` (string): Image identifier.
* Returns:
    * Image data (bytes).
    * User identifier (who published the image, string).
    * Tags (list(string)).

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

### 4.1. Relational model

There are several many-to-many relationships we need to represent. We use 'map'
tables for this purpose.

Table `users`:

* `user_id` (string, primary key): User identifier.
* `first_name` (string): First name.
* `last_name` (string): Last name.
* `joined_on` (datetime): Date and time the user registered.
* `left_on` (datetime): Date and time the user left.

Table `user_connections`:

* `user_id` (string, references users.user_id): User identifier.
* `user_ip` (string): IP address of the user.
* `connection_timestamp` (datetime): Date and time of the connection attempt.
* `success` (boolean): Whether the connection was successful.

Table `followers`:

* `follower_id` (string, references users.user_id): User who follows.
* `followee_id` (string, references users.user_id): User who is followed.
* `follow_timestamp` (datetime): When the interaction started.
* `unfollow_timestamp` (datetime): When the interaction eventually ended.

Table `images`:

* `image_id` (uuid, primary key): Image identifier.
* `image_title` (string): Image title.
* `image_path` (string): Path of the image in the storage system.
* `owner_id` (string, references users.user_id): User identifier of the image
  owner.
* `publication_timestamp` (datetime): Date and time the image was published.
* `deletion_timestamp` (datetime): Date and time the image was deleted.
* `to_be_deleted` (boolean): Whether the image was marked for deletion.
* `filter_id` (integer, references filters.filter_id): Filter identifier.

Table `filters`:

* `flter_id` (integer): Filter identifier.
* `filter_name` (integer): Filter name.

Table `tags`:

* `tag_id` (integer, primary key): Tag identifier.
* `tag_name` (string): Tag name.

Table `tag_image_map`:

* `image_id` (string, references images.image_id): Image identifier.
* `tag_id` (integer, references tags.tag_id): Tag identifier.
* `tag_timstamp (datetime): When the tag was added.
* `untag_timstamp (datetime): When the tag was eventually deleted.

Table `albums`:

* `album_id` (integer, primary key): Album identifier.
* `album_name` (string): Album name.
* `owner_id` (string, references user.user_id): User who owns the album.
* `created_on` (datetime): Date and time the album was created.
* `private` (boolean): Whether the album is private or not.

Table `album_image_map`:

* `album_id` (integer, references albums.album_id): Album identifier.
* `image_id` (string, references images.image_id): Image identifier.
* `add_timestamp` (datetime): When the image was added to the album.
* `remove_timestamp` (datetime): When the image was eventually removed.

Table `album_user_map`:

* `album_id` (integer, references albums.album_id): Album identifier.
* `user_id` (string, references users.user_id): Identifier of user authorized
  to access album.
* `add_timestamp` (datetime): When the user was added to the album.
* `remove_timestamp` (datetime): When the image was eventually removed.

Table `image_comments`:

* `image_id` (string, references images.image_id): Image identifier.
* `user_id` (string, references users.user_id): Identifier of user who
  commented.
* `comment_text` (string): Text of the comment.
* `add_timestamp` (datetime): When the comment was made.
* `delete_timestamp` (datetime): When the comment was eventually deleted.

Table `image_likes`:

* `image_id` (string, references images.image_id): Image identifier.
* `user_id` (string, references users.user_id): Identifier of user who
  liked the image.
* `like_timestamp` (datetime): When the 'like' was made.
* `dislike_timestamp` (datetime): When the 'like' was eventually removed.

## 4.2. Graph model

The relational model is complicated because it has to model several
many-to-many relationships. A graph model can represent such relationship much
more easily, which not only simplifies the schema but the queries as well.

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

## 5. High-level design

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
