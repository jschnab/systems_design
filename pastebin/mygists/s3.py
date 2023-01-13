import boto3
import botocore

from . import return_codes
from .config import config

S3_CLIENT = boto3.client("s3")


def call_s3_client(method, *args, **kwargs):
    rcode = return_codes.OK
    response = None
    try:
        response = getattr(S3_CLIENT, method)(*args, **kwargs)
        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            rcode = return_codes.UNKOWN_ERROR
    except botocore.exceptions.ClientError as e:
        rcode = return_codes.UNKNOWN_ERROR
        ecode = e.response["Error"]["Code"]
        if ecode == "AccessDenied":
            rcode = return_codes.ACCESS_DENIED
        elif ecode == "NoSuchBucket":
            rcode = return_codes.S3_BUCKET_NOT_EXISTS
        elif ecode == "NoSuchKey":
            rcode = return_codes.S3_KEY_NOT_EXISTS
    return rcode, response


def put_text(key, text_body):
    rcode, response = call_s3_client(
        "put_object",
        **dict(
            Body=text_body.encode(config["text_storage"]["encoding"]),
            Bucket=config["text_storage"]["s3_bucket"],
            Key=key,
        ),
    )
    return rcode, response


def get_text(text_id):
    rcode, response = call_s3_client(
        "get_object",
        **dict(Bucket=config["text_storage"]["s3_bucket"], Key=text_id),
    )
    if rcode is not return_codes.OK:
        return rcode, response
    return (
        rcode,
        response["Body"].read().decode(config["text_storage"]["encoding"]),
    )
