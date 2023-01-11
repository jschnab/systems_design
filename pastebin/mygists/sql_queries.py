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
  text_id VARCHAR(10),
  text_path VARCHAR(255),
  created_by VARCHAR(40) REFERENCES users(user_id),
  creation TIMESTAMP,
  expiration TIMESTAMP
);
"""

CREATE_USER = """
INSERT INTO users (user_id, first_name, last_name, joined, password)
VALUES (%s, %s, %s, %s, %s);
"""

INSERT_TEXT = "INSERT INTO texts VALUES (%s, %s, %s, %s, %s);"

GET_TEXTS_BY_USER = "SELECT * FROM texts WHERE created_by = %s;"

GET_USER = "SELECT * FROM users WHERE user_id = %s;"

UPDATE_USER_LAST_CONNECTION = """
UPDATE users SET last_connection = %s WHERE user_id = %s;
"""
