"""
CQL queries that will be converted to prepared statements are stored in
variables ending with '_QRY' so they can be identified automatically.
"""

# DDL
CREATE_KEYSPACE = """
CREATE KEYSPACE IF NOT EXISTS {keyspace}
WITH REPLICATION = {{
  'class': %s,
  'replication_factor': %s
}}
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
CREATE_USER_QRY = """
INSERT INTO users (
  user_id,
  first_name,
  last_name,
  password,
  registration_timestamp,
  album_names
)
VALUES (?, ?, ?, ?, ?, ?)
IF NOT EXISTS
;"""

INSERT_USER_FOLLOWS_QRY = """
INSERT INTO user_follows (
  follower_id,
  followed_id,
  creation_timestamp
)
VALUES (?, ?, ?)
IF NOT EXISTS
;"""

INSERT_USER_FOLLOWED_QRY = """
INSERT INTO user_followed (
  followed_id,
  follower_id,
  creation_timestamp
)
VALUES (?, ?, ?)
IF NOT EXISTS
;"""

INSERT_IMAGE_BY_USER_QRY = """
INSERT INTO images_by_user (
  owner_id,
  album_name,
  publication_timestamp,
  image_id,
  image_path
)
VALUES (?, ?, ?, ?, ?)
;"""

INSERT_IMAGE_QRY = """
INSERT INTO images (
  image_id,
  image_path,
  owner_id,
  publication_timestamp,
  description,
  tags
)
VALUES (?, ?, ?, ?, ?, ?)
;"""

TAG_IMAGE_QRY = """
UPDATE images SET tags = tags + ? WHERE image_id = ?
;"""

CREATE_ALBUM_QRY = """
INSERT INTO albums (
    album_name,
    owner_id,
    creation_timestamp
)
VALUES (?, ?, ?)
IF NOT EXISTS
;"""

ADD_ALBUM_TO_USER_QRY = """
UPDATE users SET album_names = album_names + ? WHERE user_id = ?
;"""

SET_ALBUM_FOR_IMAGE_QRY = """
UPDATE images SET album_name = ? WHERE image_id = ?
;"""

ADD_IMAGE_TO_ALBUM_QRY = """
UPDATE albums
SET image_ids = image_ids + ?
WHERE album_name = ? AND owner_id = ?
;"""

COMMENT_IMAGE_QRY = """
INSERT INTO image_comments (
    image_id,
    creation_timestamp,
    user_id,
    comment
)
VALUES (?, ?, ?, ?)
;"""

LIKE_IMAGE_QRY = """
INSERT INTO image_likes (
   image_id,
   user_id,
   creation_timestamp
)
VALUES (?, ?, ?)
;"""

RECORD_USER_CONNECTION_QRY = """
INSERT INTO user_connections (
    user_id,
    connection_timestamp,
    user_ip,
    success
)
VALUES (?, ?, ?, ?)
;"""

INCREMENT_IMAGE_POPULARITY_QRY = """
UPDATE image_popularity SET popularity = popularity + 1
WHERE image_id = ?
;"""

INSERT_USER_FEED_QRY = """
INSERT INTO user_feeds (
    user_id,
    rank,
    image_id,
    owner_id,
    image_publication_timestamp
)
VALUES (?, ?, ?, ?, ?)
;"""

# DQL
GET_IMAGE_INFO_QRY = """
SELECT * FROM images WHERE image_id = ?
;"""

GET_FOLLOWED_USERS_QRY = """
SELECT followed_id FROM user_follows WHERE follower_id = ?
ALLOW FILTERING
;"""

GET_FOLLOWER_USERS_QRY = """
SELECT follower_id FROM user_followed WHERE followed_id = ?
;"""

GET_IMAGES_BY_USER_QRY = """
SELECT image_id, image_path, publication_timestamp FROM images_by_user
WHERE owner_id = ?
;"""

GET_IMAGES_BY_ALBUM_QRY = """
SELECT image_id, publication_timestamp FROM images_by_user
WHERE owner_id = ? AND album_name = ?
;"""

GET_IMAGE_COMMENTS_QRY = "SELECT * FROM image_comments WHERE image_id = ?;"

GET_IMAGE_LIKES_QRY = "SELECT * FROM image_likes WHERE image_id = ?;"

GET_IMAGE_LIKE_BY_USER_QRY = """
SELECT * FROM image_likes WHERE image_id = ? AND user_id = ?
;"""

GET_USER_INFO_QRY = """
SELECT * FROM users WHERE user_id = ?
;"""

GET_ALBUMS_BY_USER_QRY = """
SELECT album_names FROM users WHERE user_id = ?
;"""

GET_ALBUM_INFO_QRY = """
SELECT * FROM albums WHERE album_name = ? AND owner_id = ?
;"""

GET_ALBUM_IMAGES_QRY = """
SELECT image_id, publication_timestamp FROM images_by_user
WHERE owner_id = ? AND album_name = ?
;"""

GET_RECENT_USER_CONNECTIONS_QRY = """
SELECT connection_timestamp, success
FROM user_connections
WHERE user_id = ? AND connection_timestamp >= ?
ORDER BY connection_timestamp DESC
;"""

GET_USER_IMAGES_BY_ALBUM_TIMESTAMP_QRY = """
SELECT owner_id, image_id, publication_timestamp
FROM images_by_user
WHERE owner_id = ?
AND album_name IN ?
AND publication_timestamp > ?
;"""

COUNT_USER_IMAGES_BY_ALBUM_TIMESTAMP_QRY = """
SELECT COUNT(*)
FROM images_by_user
WHERE owner_id = ?
AND album_name IN ?
AND publication_timestamp > ?
;"""

USER_EXISTS_QRY = "SELECT user_id FROM users WHERE user_id = ?;"

GET_IMAGE_POPULARITY_QRY = """
SELECT popularity from image_popularity WHERE image_id = ?
;"""

GET_FOLLOWERS_QRY = "SELECT DISTINCT follower_id FROM user_follows;"

GET_USER_FEED_QRY = """
SELECT image_id, image_publication_timestamp, owner_id
FROM user_feeds
WHERE user_id = ?
;"""
