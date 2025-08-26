import zlib

import aioboto3
import botocore

from .config import config
from .log import get_logger

LOGGER = get_logger()
SESSION = aioboto3.Session()
CONF = config["text_storage"]
BUCKET = CONF["bucket"]
ENDPOINT_URL = CONF["endpoint"]
TEXT_ENCODING = CONF["encoding"]
CLIENT_PARAMS = {
    "endpoint_url": ENDPOINT_URL,
    "aws_access_key_id": CONF["user"],
    "aws_secret_access_key": CONF["password"],
}


async def put_text(text_id, text_body):
    async with SESSION.client("s3", **CLIENT_PARAMS) as client:
        await client.put_object(
            Body=zlib.compress(text_body.encode(TEXT_ENCODING)),
            Bucket=BUCKET,
            Key=text_id,
        )


async def get_text(text_id):
    try:
        async with SESSION.client("s3", **CLIENT_PARAMS) as client:
            response = await client.get_object(Bucket=BUCKET, Key=text_id)
            body = await response["Body"].read()
            return zlib.decompress(body).decode(TEXT_ENCODING)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            LOGGER.error(f"Key '{text_id}' not found")
            return
        raise


async def delete_text(text_id):
    async with SESSION.client("s3", **CLIENT_PARAMS) as client:
        await client.delete_object(Bucket=BUCKET, Key=text_id)
