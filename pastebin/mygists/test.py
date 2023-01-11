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


def test_get_text():
    print(s3.get_text("249Y"))


def test_get_texts_by_user():
    data = database.get_texts_by_user("anonymous")
    print(data)
    print(data[0]["text_id"])
    print(data[1]["expiration"])


def main():
    test_get_text()


if __name__ == "__main__":
    main()
