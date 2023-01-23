from datetime import datetime, timedelta

from . import database
from . import object_store


def test_put_text():
    with open("config.py") as f:
        text_body = f.read()
    now = datetime.now()
    exp = now + timedelta(days=30)

    database.put_text(
        "DySG", text_body, "anonymous", now, exp,
    )


def test_put_text_object():
    object_store.put_text("this-is-the-key", "this-is-the-text-body")


def test_get_text():
    print(object_store.get_text("249Y"))


def test_get_text_no_such_key():
    print("object not found:", object_store.get_text("osidmoismdf") is None)


def test_get_texts_by_user():
    data = database.get_texts_by_user("anonymous")
    print(data)
    print(data[0]["text_id"])
    print(data[1]["expiration"])


def test_insert_user_exists():
    print(
        database.create_user(
            "anonymous", "john", "doe", datetime.now(), "blah"
        )
    )


def main():
    test_insert_user_exists()


if __name__ == "__main__":
    main()
