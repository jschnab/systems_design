import json
import os

import boto3


class ObjectStore:
    def __init__(self, bucket=None, encoding="utf-8"):
        self.bucket = bucket or os.getenv("TEXT_S3_BUCKET")
        self.encoding = encoding
        self.client = boto3.client("s3")

    def put_object(
        self, data, key, created_by, creation_timestamp, expiration_timestamp,
    ):
        response = self.client.put_object(
            Body=data.encode(self.encoding), Bucket=self.bucket, Key=key,
        )
        metadata = {
            "created_by": created_by,
            "creation_timestamp": creation_timestamp,
            "expiration_timestamp": expiration_timestamp,
        }
        response_meta = self.client.put_object(
            Body=json.dumps(metadata).encode(self.encoding),
            Bucket=self.bucket,
            Key=f"{key}.meta",
        )

    def get_object(self, key):
        response = self.client.get_object(Bucket=self.bucket, Key=key,)
        return response["Body"].decode(self.encoding)
