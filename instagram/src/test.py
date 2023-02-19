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


def database_add_image():
    database.add_image(
        image_id=uuid.uuid4(),
        image_description="sunset on the ocean",
        owner_id="jonathan",
        tags={"nofilter"},
        album_name=None,
    )


def api_put_image():
    img = Image.open("/home/jonathans/Downloads/IMG-0198.jpg")
    data = io.BytesIO()
    img.save(data, "JPEG")
    api.put_image(
        image_data=data.getvalue(),
        image_description="big house in upstate",
        user_id="jaynee",
        tags=["nofilter"],
        album_name="holidays",
    )


def database_get_image_info():
    image_id = uuid.UUID("5bf0a783-7c9b-4f84-9de6-472b464e6a6f")
    info = database.get_image_info(image_id)
    print(info)


def database_tag_image():
    image_id = uuid.UUID("5bf0a783-7c9b-4f84-9de6-472b464e6a6f")
    database.tag_image(image_id, {"happy"})


def database_create_user():
    code = database.create_user("jonathan", "jon", "schnaps", "soidfsousd8hn")
    print(code)


def database_create_album():
    code = database.create_album("visiting upstate", "jonathan")
    print(code)


def database_follow_user():
    database.follow_user("zobby", "jonathan")
    database.follow_user("zobby", "jaynee")
    database.follow_user("jaynee", "jonathan")
    database.follow_user("jonathan", "jaynee")


def database_add_image_to_album():
    image_id = uuid.UUID("fd058031-980f-4ac9-84a6-8c29954c9958")
    album_name = "visiting upstate"
    user_id = "jonathan"
    database.add_image_to_album(image_id, album_name, user_id)


def database_comment_image():
    image_id = uuid.UUID("df3bab04-4d07-485d-8c45-fbda63471a9a")
    database.comment_image(image_id, "jonathan", "nice shot man")


def database_like_image():
    image_id = uuid.UUID("5bf0a783-7c9b-4f84-9de6-472b464e6a6f")
    database.like_image(image_id, "zobby")


def database_get_followed_users():
    print(database.get_followed_users("zobby"))


def database_get_follower_users():
    print(database.get_follower_users("jonathan"))


def database_get_images_by_user():
    print(database.get_images_by_user("jonathan"))


def database_get_image_comments():
    image_id = uuid.UUID("5bf0a783-7c9b-4f84-9de6-472b464e6a6f")
    print(database.get_image_comments(image_id))


def database_get_image_likes():
    image_id = uuid.UUID("0a275ea3-7293-4a86-97b5-03c1f3443a09")
    print(database.get_image_likes(image_id))


def database_get_image_like_by_user():
    image_id = uuid.UUID("0a275ea3-7293-4a86-97b5-03c1f3443a09")
    print(database.get_image_like_by_user(image_id, 'jonathan'))


def database_get_user_info():
    print(database.get_user_info("jonathan"))


def database_get_albums_by_user():
    print(database.get_albums_by_user("jonathan"))
    print(database.get_albums_by_user("dude"))


def database_get_album_info():
    print(database.get_album_info("visiting upstate", "jonathan"))


def main():
    database_get_image_like_by_user()


if __name__ == "__main__":
    main()
