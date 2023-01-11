"""
Functions in this module assume that:

* a Postgres version >= 12 is used
* the following environment variables are defined:
    * MYPASTEBIN_DB_HOST
    * MYPASTEBIN_DB_PORT
    * MYPASTEBIN_DB_DATABASE
    * MYPASTEBIN_DB_USER
    * MYPASTEBIN_DB_PASSWORD
    * MYPASTEBIN_S3_BUCKET
"""
import os

import boto3
import psycopg2
import psycopg2.errors
import psycopg2.extensions
import psycopg2.extras

import postgres


class DataStore:
    def __init__(self):
        self.db = postgres.DB(
            host=os.getenv("MYPASTEBIN_DB_HOST"),
            port=os.getenv("MYPASTEBIN_DB_PORT"),
            database=os.getenv("MYPASTEBIN_DB_DATABASE"),
            user=os.getenv("MYPASTEBIN_DB_USER"),
            password=os.getenv("MYPASTEBIN_DB_PASSWORD"),
        )
        self.bucket = os.getenv("MYPASTEBIN_S3_BUCKET")
        self.encoding = os.getenv("MYPASTEBIN_TEXT_ENCODING", "utf-8")
        self.s3_client = boto3.client("s3")

    def put_text(
        self,
        text_id,
        text_body,
        user_id,
        creation_timestamp,
        expiration_timestamp,
    ):
        response = self.s3_client.put_object(
            Body=text_body.encode(self.encoding),
            Bucket=self.bucket,
            Key=text_id,
        )

        with self.db.con.cursor() as cur:
            cur.execute(
                "INSERT INTO texts values (%s, %s, %s, %s, %s);",
                (
                    text_id,
                    f"{self.bucket}/{text_id}",
                    user_id,
                    creation_timestamp,
                    expiration_timestamp,
                ),
            )
        self.db.con.commit()

    def get_text(self, text_id):
        response = self.s3_client.get_object(Bucket=self.bucket, Key=text_id,)
        return response["Body"].read().decode(self.encoding)

    def get_texts_by_user(self, username):
        with self.db.con.cursor(
            cursor_factory=psycopg2.extras.DictCursor
        ) as cur:
            cur.execute(
                "SELECT * FROM texts WHERE created_by = '%s';", (username,)
            )
            return cur.fetchall()
