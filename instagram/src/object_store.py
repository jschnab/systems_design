import boto3
import botocore

from .config import CONFIG

S3_CLIENT = boto3.client("s3")
S3_BUCKET = CONFIG["image_store"]["s3_bucket"]


def put_image(image_id, image_data):
    S3_CLIENT.put_object(
        Body=image_data,
        Bucket=S3_BUCKET,
        Key=image_id,
    )


def get_image(image_id):
    try:
        response = S3_CLIENT.get_object(Bucket=S3_BUCKET, Key=image_id)
        return response["Body"].read()
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return
        raise


def delete_image(image_id):
    S3_CLIENT.delete_object(Bucket=S3_BUCKET, Key=image_id)
