import zlib

import boto3
import botocore

from .config import config

S3_CLIENT = boto3.client("s3")
S3_BUCKET = config["text_storage"]["s3_bucket"]
TEXT_ENCODING = config["text_storage"]["encoding"]


def put_text(text_id, text_body):
    S3_CLIENT.put_object(
        Body=zlib.compress(text_body.encode(TEXT_ENCODING)),
        Bucket=S3_BUCKET,
        Key=text_id,
    )


def get_text(text_id):
    try:
        response = S3_CLIENT.get_object(Bucket=S3_BUCKET, Key=text_id)
        return zlib.decompress(response["Body"].read()).decode(TEXT_ENCODING)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return
        raise


def delete_text(text_id):
    # There is no error if the object does not exist.
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/
    # services/s3.html#S3.Client.delete_object
    S3_CLIENT.delete_object(Bucket=S3_BUCKET, Key=text_id)
