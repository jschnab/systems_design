import datetime
import os

import motor.motor_asyncio


def get_client():
    return motor.motor_asyncio.AsyncIOMotorClient(
        os.getenv("APP_DB_HOST", "localhost"),
        int(os.getenv("APP_DB_PORT", 27017))
    )


async def insert(collection, document):
    result = await collection.insert_one(document)
    print(repr(result.inserted_id))


def test_insert():
    doc = {
        "_id": "jdoe",
        "first_name": "John",
        "last_name": "Doe",
        "joined_on": datetime.datetime.now(),
    }
    client = get_client()
    db = client.shorturls
    users = db.users
    loop = client.get_io_loop()
    loop.run_until_complete(insert(users, doc))


def create_url(alias, original, user_name, ttl, client):
    now = datetime.datetime.now()
    doc = {
        "_id": alias,
        "origina": original,
        "created_by": user_name,
        "created_on": now,
        "ttl": now + datetime.timedelta(hours=ttl),
    }
    client.shorturls.urls.insert_one(doc)


def test_create_url():
    client = get_client()
    try:
        create_url(
            "abcd",
            "https://www.google.com",
            "anonymous",
            24,
            client,
        )
    except Exception as e:
        print(e)
    finally:
        client.close


def get_url(alias, client):
    result = client.shorturls.urls.find_one(
        {"_id": alias}, {"_id": 0, "original": 1}
    )
    if result is not None:
        return result


def test_get_url():
    client = get_client()
    try:
        print(get_url("abcd", client))
        print(get_url("cpoi", client))
    except Exception as e:
        print(e)
    finally:
        client.close


if __name__ == "__main__":
    test_get_url()
