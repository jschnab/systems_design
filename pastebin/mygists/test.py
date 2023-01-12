from datetime import datetime, timedelta

from . import database
from . import s3


def test_put_text():
    with open("config.py") as f:
        text_body = f.read()
    now = datetime.now()
    exp = now + timedelta(days=30)

    database.put_text(
        "DySG",
        text_body,
        "anonymous",
        now,
        exp,
    )


def test_s3_put_text():
    rcode, data = s3.put_text("this-is-the-key", "this-is-the-text-body")
    if rcode is not None:
        print(rcode, data)


def test_get_text():
    print(s3.get_text("249Y"))


def test_get_text_no_such_key():
    print(s3.get_text("osidmoismdf"))


def test_get_texts_by_user():
    data = database.get_texts_by_user("anonymous")
    print(data)
    print(data[0]["text_id"])
    print(data[1]["expiration"])


def test_insert_user_exists():
    database.create_user("anonymous", "john", "doe", datetime.now(), "blah")


def main():
    test_get_text_no_such_key()


if __name__ == "__main__":
    main()
