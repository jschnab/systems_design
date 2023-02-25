from datetime import datetime, timedelta

from . import database


def truncate_hours(ts):
    return ts.replace(minute=0, second=0, microsecond=0)


def flatten_feed(images, user_id):
    result = []
    for idx, img in enumerate(images):
        result.extend(
            [
                user_id,
                idx,
                img["image_id"],
                img["owner_id"],
                img["publication_timestamp"],
            ]
        )
    return result


def user_feed_images(user_id):
    result = []
    followed_users = database.get_followed_users(user_id)
    timestamp = datetime.now() - timedelta(days=7)
    for user in followed_users:
        images = database.get_user_images_by_album_timestamp(
            user, database.get_albums_by_user(user), timestamp
        )
        for image in images:
            image["popularity"] = database.get_image_popularity(
                image["image_id"]
            )
        result.extend(images)
    return sorted(
        result,
        key=lambda x: (
            truncate_hours(x["publication_timestamp"]),
            x["popularity"],
        ),
        reverse=True,
    )[:100]


def make_user_feeds():
    followers = database.get_followers()
    for fo in followers:
        user_id = fo["follower_id"]
        images = user_feed_images(user_id)
        database.insert_feed_images(
            len(images),
            flatten_feed(images, user_id)
        )
