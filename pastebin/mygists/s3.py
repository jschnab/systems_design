import functools

import boto3
import botocore

from . import return_codes
from .config import config

S3_CLIENT = boto3.client("s3")


def manage_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except botocore.exceptions.ClientError as e:
            rcode = return_codes.UNKNOWN_ERROR
            ecode = e.response["Error"]["Code"]
            if ecode == "AccessDenied":
                rcode = return_codes.ACCESS_DENIED
            elif ecode == "NoSuchBucket":
                rcode = return_codes.S3_BUCKET_NOT_EXISTS
            elif ecode == "NoSuchKey":
                rcode = return_codes.S3_KEY_NOT_EXISTS
            return rcode, None

    return wrapper


def check_aws_response(response):
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        return return_codes.UNKNOWN_ERROR
    return return_codes.OK


@manage_exceptions
def put_text(key, text_body):
    response = S3_CLIENT.put_object(
        Body=text_body.encode(config["text_storage"]["encoding"]),
        Bucket=config["text_storage"]["s3_bucket"],
        Key=key,
    )
    return return_codes.OK, response


@manage_exceptions
def get_text(text_id):
    response = S3_CLIENT.get_object(
        Bucket=config["text_storage"]["s3_bucket"], Key=text_id,
    )
    rcode = check_aws_response(response)
    if rcode is return_codes.OK:
        return (
            rcode,
            response["Body"].read().decode(config["text_storage"]["encoding"]),
        )
    return rcode, response
