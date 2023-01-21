CREATE_TABLE_USERS = """
CREATE TABLE users (
  user_id VARCHAR(40) PRIMARY KEY,
  first_name VARCHAR(40),
  last_name VARCHAR(40),
  joined TIMESTAMP,
  last_connection TIMESTAMP,
  password VARCHAR(255)
);
"""

CREATE_TABLE_TEXTS = """
CREATE TABLE texts (
  text_id VARCHAR(255) PRIMARY KEY,
  text_path VARCHAR(255),
  user_id VARCHAR(40) REFERENCES users(user_id),
  user_ip VARCHAR(15),
  creation TIMESTAMP,
  expiration TIMESTAMP
);
"""

CREATE_INDEX_TEXTS_USERID = """
CREATE INDEX texts_userid_idx ON texts (user_id);
"""

CREATE_INDEX_TEXTS_USERIP = """
CREATE INDEX texts_userip_idx ON texts (user_ip);
"""

CREATE_INDEX_TEXTS_CREATION = """
CREATE INDEX texts_creation_idx ON texts (creation);
"""

CREATE_USER = """
INSERT INTO users (user_id, first_name, last_name, joined, password)
VALUES (%s, %s, %s, %s, %s);
"""

INSERT_TEXT = "INSERT INTO texts VALUES (%s, %s, %s, %s, %s);"

DELETE_TEXT = "DELETE FROM texts WHERE text_id = %s;"

GET_TEXTS_BY_USER = "SELECT * FROM texts WHERE created_by = %s;"

GET_USER = "SELECT * FROM users WHERE user_id = %s;"

UPDATE_USER_LAST_CONNECTION = """
UPDATE users SET last_connection = %s WHERE user_id = %s;
"""

COUNT_TEXTS_ANONYMOUS = """
SELECT COUNT(*) FROM texts
WHERE user_ip = %s AND creation > NOW() - INTERVAL '1 day';
"""

COUNT_TEXTS_USER = """
SELECT COUNT(*) FROM texts
WHERE user_id = %s AND creation > NOW() - INTERVAL '1 day';
"""
