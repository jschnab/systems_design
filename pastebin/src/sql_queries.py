CREATE_DATABASE = """
CREATE DATABASE IF NOT EXISTS {database_name}
"""

CREATE_DB_USER = """
CREATE USER IF NOT EXISTS '{user_name}'@'%' IDENTIFIED BY '{password}'
"""

CREATE_DB_USER_PERMISSIONS = """
GRANT ALL PRIVILEGES ON {database_name}.* TO '{user_name}'
"""

CREATE_TABLE_USERS = """
CREATE TABLE IF NOT EXISTS users (
  user_id VARCHAR(40) PRIMARY KEY,
  first_name VARCHAR(40),
  last_name VARCHAR(40),
  joined TIMESTAMP,
  password VARCHAR(255)
)
;"""

CREATE_TABLE_USER_CONNECTIONS = """
CREATE TABLE IF NOT EXISTS user_connections (
  user_id VARCHAR(40) REFERENCES users(user_id),
  user_ip VARCHAR(15),
  ts TIMESTAMP,
  success BOOLEAN
)
;"""

CREATE_INDEX_USER_CONNECT_TS = """
CREATE INDEX IF NOT EXISTS user_connect_ts_idx ON user_connections (ts)
;"""

CREATE_TABLE_TEXTS = """
CREATE TABLE IF NOT EXISTS texts (
  text_id VARCHAR(255) PRIMARY KEY,
  text_title VARCHAR(255),
  text_path VARCHAR(255),
  user_id VARCHAR(40) REFERENCES users(user_id),
  user_ip VARCHAR(15),
  creation TIMESTAMP,
  expiration TIMESTAMP,
  to_be_deleted BOOLEAN,
  deletion TIMESTAMP
)
;"""

CREATE_INDEX_TEXTS_USERID = """
CREATE INDEX IF NOT EXISTS texts_userid_idx ON texts (user_id)
;"""

CREATE_INDEX_TEXTS_USERIP = """
CREATE INDEX IF NOT EXISTS texts_userip_idx ON texts (user_ip)
;"""

CREATE_INDEX_TEXTS_CREATION = """
CREATE INDEX IF NOT EXISTS texts_creation_idx ON texts (creation)
;"""

CREATE_USER = """
INSERT INTO users (user_id, first_name, last_name, joined, password)
VALUES (%s, %s, %s, %s, %s)
;"""

CREATE_ANONYMOUS_USER = "INSERT INTO users (user_id) VALUES (%s);"

INSERT_TEXT = """
INSERT INTO texts (
    text_id
    , text_title
    , text_path
    , user_id
    , user_ip
    , creation
    , expiration
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
;"""

MARK_TEXT_FOR_DELETION = """
UPDATE texts SET to_be_deleted = true WHERE text_id = %s
;"""

MARK_TEXT_DELETED = "UPDATE texts SET deletion = %s WHERE text_id = %s;"

GET_TEXTS_BY_OWNER = """
SELECT text_id, text_title, creation, expiration FROM texts
WHERE user_id = %s AND (deletion IS NULL AND to_be_deleted IS NOT TRUE)
ORDER BY creation
;"""

GET_TEXT_OWNER = "SELECT user_id FROM texts WHERE text_id = %s;"

GET_TEXTS_FOR_DELETION = """
SELECT text_id FROM texts
WHERE (expiration < NOW() OR to_be_deleted) AND deletion IS NULL
;"""

GET_USER = "SELECT * FROM users WHERE user_id = %s;"

UPDATE_USER_LAST_CONNECTION = """
UPDATE users SET last_connection = %s WHERE user_id = %s
;"""

COUNT_TEXTS_ANONYMOUS = """
SELECT COUNT(*) AS quota FROM texts
WHERE user_ip = %s AND creation > NOW() - INTERVAL 1 DAY
;"""

COUNT_TEXTS_USER = """
SELECT COUNT(*) AS quota FROM texts
WHERE user_id = %s AND creation > NOW() - INTERVAL 1 DAY
;"""

RECORD_USER_CONNECT = """
INSERT INTO user_connections (user_id, user_ip, ts, success)
VALUES (%s, %s, NOW(), %s)
;"""

GET_RECENT_USER_CONNECTIONS = """
SELECT ts, success FROM user_connections
WHERE user_id = %s AND ts >= NOW() - INTERVAL 15 MINUTE
ORDER BY ts DESC
;"""
