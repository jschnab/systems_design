# DDL
CREATE_KEYSPACE = """
CREATE KEYSPACE IF NOT EXISTS %(keyspace_name)s
WITH REPLICATION = {'class': 'SimpleStrategy'}
;"""

CREATE_TABLE_USERS = """
CREATE TABLE IF NOT EXISTS instagram.users (
  user_id TEXT PRIMARY KEY,
  first_name TEXT,
  last_name TEXT,
  password TEXT,
  creation_timestamp TIMESTAMP,
  deletion_timestamp TIMESTAMP,
  albums_owns SET <BIGINT>,
  albums_can_access SET <BIGINT>
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
;"""

CREATE_TABLE_FOLLOWERS = """
CREATE TABLE IF NOT EXISTS followers (
  follower_id TEXT,
  followee_id TEXT,
  follow_timestamp TIMESTAMP,
  unfollow_timestamp TIMESTAMP,
  PRIMARY KEY (follower_id, followee_id)
)
;"""

CREATE_TABLE_IMAGES = """
CREATE TABLE IF NOT EXISTS images (
  image_id UUID PRIMARY KEY,
  image_title TEXT,
  image_path TEXT,
  owner_id TEXT,
  album_name TEXT,
  publication_timestamp TIMESTAMP,
  deletion_timestamp TIMESTAMP,
  to_be_deleted BOOLEAN,
  filter TEXT,
  tags SET <TEXT>
)
;"""

CREATE_TABLE_ALBUMS = """
CREATE TABLE IF NOT EXISTS albums (
  album_name TEXT,
  owner_id TEXT,
  creation_timestamp TIMESTAMP,
  deletion_timestamp TIMESTAMP,
  private BOOLEAN,
  user_ids SET<TEXT>,
  PRIMARY KEY (album_name, owner_id)
)
;"""

CREATE_TABLE_IMAGE_COMMENTS = """
CREATE TABLE IF NOT EXISTS image_comments (
  image_id UUID,
  user_id TEXT,
  comment TEXT,
  creation_timestamp TIMESTAMP,
  deletion_timestamp TIMESTAMP,
  PRIMARY KEY (image_id, user_id, creation_timestamp)
)
;"""

CREATE_TABLE_IMAGE_LIKES = """
CREATE TABLE IF NOT EXISTS image_likes (
  image_id UUID,
  user_id TEXT,
  like_timestamp TIMESTAMP,
  dislike_timestamp TIMESTAMP,
  PRIMARY KEY (image_id, user_id, like_timestamp)
)
;"""

# DML
CREATE_USER = """
INSERT INTO users (
    user_id,
    first_name,
    last_name,
    password,
    creation_timestamp
)
VALUES (%s, %s, %s, %s, %s)
IF NOT EXISTS
;"""

INSERT_IMAGE = """
INSERT INTO images (
    image_id,
    image_title,
    image_path,
    owner_id,
    album_name,
    publication_timestamp,
    filter,
    tags
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
IF NOT EXISTS
;"""

DELETE_IMAGE = "UPDATE images SET deletion_timestamp = %s WHERE image_id = %s;"

CREATE_ALBUM = """
INSERT INTO albums (
    album_name,
    owner_id,
    creation_timestamp,
    private,
    user_ids
)
VALUES (%s, %s, %s, %s, %s)
IF NOT EXISTS
;"""

MOVE_IMAGE_TO_ALBUM = "UPDATE images SET album_name = %s WHERE image_id = %s;"

COMMENT_IMAGE = """
INSERT INTO image_comments (
    image_id,
    user_id,
    creation_timestamp,
    comment
)
VALUES (%s, %s, %s, %s)
IF NOT EXISTS
;"""

LIKE_IMAGE = """
INSERT INTO image_likes (
   image_id,
   user_id,
   like_timestamp
)
VALUES (%s, %s, %s)
IF NOT EXISTS
;"""

FOLLOW_USER = """
INSERT INTO followers (
   follower_id,
   followee_id,
   follow_timestamp
)
VALUES (%s, %s, %s)
;"""
