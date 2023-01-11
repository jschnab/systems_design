CREATE_TABLE_USERS = """
CREATE TABLE users (
  user_id VARCHAR(40) PRIMARY KEY,
  first_name VARCHAR(40),
  last_name VARCHAR(40),
  joined TIMESTAMP,
  last_connection TIMESTAMP
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
