# DDL
CREATE_KEYSPACE = """
CREATE KEYSPACE IF NOT EXISTS %(keyspace_name)s
WITH REPLICATION = {
  'class': %(replication_strategy)s,
  'replication_factor': %(replication_factor)s
}
;"""

CREATE_TABLE_IMAGES_BY_USER = """
CREATE TABLE IF NOT EXISTS images_by_user (
  owner_id TEXT,
  album_name TEXT,
  publication_timestamp TIMESTAMP,
  image_id UUID,
  image_path TEXT,
  PRIMARY KEY (owner_id, album_name, publication_timestamp)
)
WITH CLUSTERING ORDER BY (album_name ASC, publication_timestamp DESC)
;"""

CREATE_TABLE_IMAGES = """
CREATE TABLE IF NOT EXISTS images (
  image_id UUID PRIMARY KEY,
  image_path TEXT,
  owner_id TEXT,
  publication_timestamp TIMESTAMP,
  description TEXT,
  album_name TEXT,
  tags SET<TEXT>
)
;"""

CREATE_TABLE_IMAGE_COMMENTS = """
CREATE TABLE IF NOT EXISTS image_comments (
  image_id UUID,
  creation_timestamp TIMESTAMP,
  user_id TEXT,
  comment TEXT,
  PRIMARY KEY (image_id, creation_timestamp, user_id)
)
WITH CLUSTERING ORDER BY (creation_timestamp DESC, user_id ASC)
;"""

CREATE_TABLE_IMAGE_LIKES = """
CREATE TABLE IF NOT EXISTS image_likes (
  image_id UUID,
  user_id TEXT,
  creation_timestamp TIMESTAMP,
  PRIMARY KEY (image_id, user_id)
)
;"""

CREATE_TABLE_USERS = """
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  registration_timestamp TIMESTAMP,
  first_name TEXT,
  last_name TEXT,
  password TEXT,
  album_names SET<TEXT>,
)
;"""

CREATE_TABLE_USER_FOLLOWS = """
CREATE TABLE IF NOT EXISTS user_follows (
  follower_id TEXT,
  followed_id TEXT,
  creation_timestamp TIMESTAMP,
  PRIMARY KEY (follower_id, followed_id)
)
;"""

CREATE_TABLE_USER_FOLLOWED = """
CREATE TABLE IF NOT EXISTS user_followed (
  followed_id TEXT,
  follower_id TEXT,
  creation_timestamp TIMESTAMP,
  PRIMARY KEY (followed_id, follower_id)
)
;"""

CREATE_TABLE_ALBUMS = """
CREATE TABLE IF NOT EXISTS albums (
  album_name TEXT,
  owner_id TEXT,
  creation_timestamp TIMESTAMP,
  image_ids SET<UUID>,
  PRIMARY KEY (album_name, owner_id)
)
;"""

CREATE_TABLE_USER_CONNECTIONS = """
CREATE TABLE IF NOT EXISTS user_connections (
  user_id TEXT,
  connection_timestamp TIMESTAMP,
  user_ip INET,
  success BOOLEAN,
  PRIMARY KEY (user_id, connection_timestamp)
)
WITH CLUSTERING ORDER BY (connection_timestamp DESC)
;"""

CREATE_TABLE_IMAGE_POPULARITY = """
CREATE TABLE IF NOT EXISTS image_popularity (
  image_id UUID PRIMARY KEY,
  popularity COUNTER
)
;"""

CREATE_TABLE_USER_FEEDS = """
CREATE TABLE IF NOT EXISTS user_feeds (
  user_id TEXT,
  rank SMALLINT,
  image_id UUID,
  owner_id TEXT,
  image_publication_timestamp TIMESTAMP,
  PRIMARY KEY (user_id, rank)
)
;"""

# DML
CREATE_USER = """
INSERT INTO users (
  user_id,
  first_name,
  last_name,
  password,
  registration_timestamp,
  album_names
)
VALUES (%s, %s, %s, %s, %s, %s)
IF NOT EXISTS
;"""

INSERT_USER_FOLLOWS = """
INSERT INTO user_follows (
  follower_id,
  followed_id,
  creation_timestamp
)
VALUES (%s, %s, %s)
IF NOT EXISTS
;"""

INSERT_USER_FOLLOWED = """
INSERT INTO user_followed (
  followed_id,
  follower_id,
  creation_timestamp
)
VALUES (%s, %s, %s)
IF NOT EXISTS
;"""

INSERT_IMAGE_BY_USER = """
INSERT INTO images_by_user (
  owner_id,
  album_name,
  publication_timestamp,
  image_id,
  image_path
)
VALUES (%s, %s, %s, %s, %s)
;"""

INSERT_IMAGE = """
INSERT INTO images (
  image_id,
  image_path,
  owner_id,
  publication_timestamp,
  description,
  tags
)
VALUES (%s, %s, %s, %s, %s, %s)
;"""

TAG_IMAGE = """
UPDATE images SET tags = tags + %s WHERE image_id = %s
;"""

CREATE_ALBUM = """
INSERT INTO albums (
    album_name,
    owner_id,
    creation_timestamp
)
VALUES (%s, %s, %s)
IF NOT EXISTS
;"""

ADD_ALBUM_TO_USER = """
UPDATE users SET album_names = album_names + {%s} WHERE user_id = %s
;"""

SET_ALBUM_FOR_IMAGE = "UPDATE images SET album_name = %s WHERE image_id = %s;"

ADD_IMAGE_TO_ALBUM = """
UPDATE albums
SET image_ids = image_ids + {%s}
WHERE album_name = %s AND owner_id = %s
;"""

COMMENT_IMAGE = """
INSERT INTO image_comments (
    image_id,
    creation_timestamp,
    user_id,
    comment
)
VALUES (%s, %s, %s, %s)
;"""

LIKE_IMAGE = """
INSERT INTO image_likes (
   image_id,
   user_id,
   creation_timestamp
)
VALUES (%s, %s, %s)
;"""

RECORD_USER_CONNECTION = """
INSERT INTO user_connections (
    user_id,
    connection_timestamp,
    user_ip,
    success
)
VALUES (%s, %s, %s, %s)
;"""

INCREMENT_IMAGE_POPULARITY = """
UPDATE image_popularity SET popularity = popularity + 1
WHERE image_id = %s
;"""

INSERT_USER_FEED = """
INSERT INTO user_feeds (
    user_id,
    rank,
    image_id,
    owner_id,
    image_publication_timestamp
)
VALUES (%s, %s, %s, %s, %s)
;"""

# DQL
GET_IMAGE_INFO = """
SELECT * FROM images WHERE image_id = %s
;"""

GET_FOLLOWED_USERS = """
SELECT followed_id FROM user_follows WHERE follower_id = %s
ALLOW FILTERING
;"""

GET_FOLLOWER_USERS = """
SELECT follower_id FROM user_followed WHERE followed_id = %s
;"""

GET_IMAGES_BY_USER = """
SELECT image_id, image_path, publication_timestamp FROM images_by_user
WHERE owner_id = %s
;"""

GET_IMAGES_BY_ALBUM = """
SELECT image_id, publication_timestamp FROM images_by_user
WHERE owner_id = %s AND album_name = %s
;"""

GET_IMAGE_COMMENTS = "SELECT * FROM image_comments WHERE image_id = %s;"

GET_IMAGE_LIKES = "SELECT * FROM image_likes WHERE image_id = %s;"

GET_IMAGE_LIKE_BY_USER = """
SELECT * FROM image_likes WHERE image_id = %s AND user_id = %s
;"""

GET_USER_INFO = """
SELECT * FROM users WHERE user_id = %s
;"""

GET_ALBUMS_BY_USER = """
SELECT album_names FROM users WHERE user_id = %s
;"""

GET_ALBUM_INFO = """
SELECT * FROM albums WHERE album_name = %s AND owner_id = %s
;"""

GET_ALBUM_IMAGES = """
SELECT image_id, publication_timestamp FROM images_by_user
WHERE owner_id = %s AND album_name = %s
;"""

GET_RECENT_USER_CONNECTIONS = """
SELECT connection_timestamp, success
FROM user_connections
WHERE user_id = %s AND connection_timestamp >= %s
ORDER BY connection_timestamp DESC
;"""

GET_USER_IMAGES_BY_ALBUM_TIMESTAMP = """
SELECT owner_id, image_id, publication_timestamp
FROM images_by_user
WHERE owner_id = %s
AND album_name IN %s
AND publication_timestamp > %s
;"""

COUNT_USER_IMAGES_BY_ALBUM_TIMESTAMP = """
SELECT COUNT(*)
FROM images_by_user
WHERE owner_id = %s
AND album_name IN %s
AND publication_timestamp > %s
;"""

USER_EXISTS = "SELECT user_id FROM users WHERE user_id = %s;"

GET_IMAGE_POPULARITY = """
SELECT popularity from image_popularity WHERE image_id = %s
;"""

GET_FOLLOWERS = "SELECT DISTINCT follower_id FROM user_follows;"

GET_USER_FEED = """
SELECT image_id, image_publication_timestamp, owner_id
FROM user_feeds
WHERE user_id = %s
;"""
