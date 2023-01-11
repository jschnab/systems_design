import boto3

from .config import config

s3_client = boto3.client("s3")


def put_text(key, text_body):
    s3_client.put_object(
        Body=text_body.encode(config["text_storage"]["encoding"]),
        Bucket=config["text_storage"]["s3_bucket"],
        Key=key,
    )


def get_text(text_id):
    response = s3_client.get_object(
        Bucket=config["text_storage"]["s3_bucket"],
        Key=text_id,
    )
    return response["Body"].read().decode(config["text_storage"]["encoding"])
