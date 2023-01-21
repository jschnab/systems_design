import boto3
import botocore

from .config import config

S3_CLIENT = boto3.client("s3")
S3_BUCKET = config["text_storage"]["s3_bucket"]
TEXT_ENCODING = config["text_storage"]["encoding"]


def put_text(text_id, text_body):
    S3_CLIENT.put_object(
        Body=text_body.encode(TEXT_ENCODING),
        Bucket=S3_BUCKET,
        Key=text_id,
    )


def get_text(text_id):
    try:
        response = S3_CLIENT.get_object(Bucket=S3_BUCKET, Key=text_id)
        return (
            response["Body"].read().decode(TEXT_ENCODING)
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return
        raise


def delete_text(text_id):
    S3_CLIENT.delete_object(Bucket=S3_BUCKET, Key=text_id)
