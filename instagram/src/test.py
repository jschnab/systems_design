import io
import uuid

from PIL import Image

from . import api
from . import database
from . import image
from . import object_store


def image_process_upload():
    img = Image.open("/home/jonathans/Downloads/helloe.bmp")
    data = io.BytesIO()
    img.save(data, "BMP")
    im, thumb = image.process_image(data.getvalue())
    object_store.put_image("test", im)
    object_store.put_image("test.thumb", thumb)


def api_publish_image():
    img = Image.open("/home/jonathans/Downloads/IMG-0198.jpg")
    data = io.BytesIO()
    img.save(data, "JPEG")
    api.publish_image(
        image_data=data.getvalue(),
        image_title="big house",
        user_id="jonathan",
        tags=["nofilter"],
        album_id=None,
        filter_name=None,
    )


def database_put_album():
    database.put_album(
        album_name="summer of love",
        owner_id="jonathan",
        user_ids={"alice", "bob"},
    )


def api_delete_image():
    image_id = uuid.UUID("ed7d86ac-ff69-490c-a3ed-f9ceaaad6f03")
    api.delete_image(image_id)


def database_move_image_to_album():
    image_id = uuid.UUID("9aaa5ea3-4013-476a-8bd7-9c7d9edc04a2")
    database.move_image_to_album(image_id, "summer of love")


def database_image_comment():
    image_id = uuid.UUID("9aaa5ea3-4013-476a-8bd7-9c7d9edc04a2")
    database.put_image_comment(
        image_id,
        "jonathan",
        "this is a great picture",
    )


def database_image_like():
    image_id = uuid.UUID("9aaa5ea3-4013-476a-8bd7-9c7d9edc04a2")
    database.put_image_like(image_id, "jonathan")


def database_follow_user():
    database.follow_user("jonathan", "jaynee")


def database_create_user():
    database.create_user("jonathan", "john", "schnaps", "soidfsousd8hn")
    database.create_user("jaynee", "jay", "nee", "soidfsousd8hn")


def main():
    database_follow_user()


if __name__ == "__main__":
    main()
