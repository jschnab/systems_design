import zlib

import aioboto3
import botocore

from .config import config
from .log import get_logger

LOGGER = get_logger()
SESSION = aioboto3.Session()
S3_BUCKET = config["text_storage"]["s3_bucket"]
TEXT_ENCODING = config["text_storage"]["encoding"]


async def put_text(text_id, text_body):
    async with SESSION.client("s3") as s3:
        await s3.put_object(
            Body=zlib.compress(text_body.encode(TEXT_ENCODING)),
            Bucket=S3_BUCKET,
            Key=text_id,
        )


async def get_text(text_id):
    try:
        async with SESSION.client("s3") as s3:
            response = await s3.get_object(Bucket=S3_BUCKET, Key=text_id)
            body = await response["Body"].read()
            return zlib.decompress(body).decode(TEXT_ENCODING)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            LOGGER.error(f"Key '{text_id}' not found")
            return
        raise


async def delete_text(text_id):
    async with SESSION.client("s3") as s3:
        await s3.delete_object(Bucket=S3_BUCKET, Key=text_id)
