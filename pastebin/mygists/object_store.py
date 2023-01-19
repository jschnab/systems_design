import boto3
import botocore

from .config import config

S3_CLIENT = boto3.client("s3")


def put_text(key, text_body):
    S3_CLIENT.put_object(
        Body=text_body.encode(config["text_storage"]["encoding"]),
        Bucket=config["text_storage"]["s3_bucket"],
        Key=key,
    )


def get_text(text_id):
    try:
        response = S3_CLIENT.get_object(
            Bucket=config["text_storage"]["s3_bucket"], Key=text_id,
        )
        return (
            response["Body"].read().decode(config["text_storage"]["encoding"])
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return
        raise
