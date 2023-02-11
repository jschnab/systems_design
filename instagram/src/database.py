from datetime import datetime

from cassandra.cluster import (
    Cluster,
    ExecutionProfile,
    EXEC_PROFILE_DEFAULT,
)

from .config import CONFIG
from . import cql_queries


def configure_session():
    profile = ExecutionProfile(
        consistency_level=CONFIG["database"].getint("consistency_level"),
        request_timeout=CONFIG["database"].getint("request_timeout"),
    )
    cluster = Cluster(
        CONFIG["database"]["endpoints"].split(","),
        port=CONFIG["database"]["port"],
        execution_profiles={EXEC_PROFILE_DEFAULT: profile},
    )
    return cluster.connect(CONFIG["database"]["keyspace_name"])


SESSION = configure_session()


def execute_query(query, params=None, session=None):
    session = session or SESSION
    return session.execute(query, params).all()


def create_table_users():
    execute_query(cql_queries.CREATE_TABLE_USERS)


def create_table_user_connections():
    execute_query(cql_queries.CREATE_TABLE_USER_CONNECTIONS)


def create_table_followers():
    execute_query(cql_queries.CREATE_TABLE_FOLLOWERS)


def create_table_images():
    execute_query(cql_queries.CREATE_TABLE_IMAGES)


def create_table_albums():
    execute_query(cql_queries.CREATE_TABLE_ALBUMS)


def create_table_image_comments():
    execute_query(cql_queries.CREATE_TABLE_IMAGE_COMMENTS)


def create_table_image_likes():
    execute_query(cql_queries.CREATE_TABLE_IMAGE_LIKES)


def create_database_objects():
    create_table_users()
    create_table_user_connections()
    create_table_followers()
    create_table_images()
    create_table_albums()
    create_table_image_comments()
    create_table_image_likes()


def create_user(user_id, first_name, last_name, password):
    execute_query(
        cql_queries.CREATE_USER,
        params=(
            user_id,
            first_name,
            last_name,
            password,
            datetime.now(),
        )
    )


def put_image_metadata(
    image_id,
    image_title,
    owner_id,
    tags,
    album_id,
    filter_name,
):
    execute_query(
        cql_queries.INSERT_IMAGE,
        params=(
            image_id,
            image_title,
            f"{CONFIG['image_store']['s3_bucket']}/{image_id}",
            owner_id,
            album_id,
            datetime.now(),
            filter_name,
            tags,
        ),
    )


def mark_image_deleted(image_id):
    """
    Mark an image as deleted.

    :param uuid.UUID image_id: Image identifier.
    :returns: None.
    """
    execute_query(
        cql_queries.DELETE_IMAGE,
        params=(datetime.now(), image_id),
    )


def put_album(album_name, owner_id, user_ids, private=False):
    execute_query(
        cql_queries.CREATE_ALBUM,
        params=(
            album_name,
            owner_id,
            datetime.now(),
            private,
            set(user_ids),
        ),
    )


def move_image_to_album(image_id, album_name):
    """
    Move an image to an album.

    :param uuid.UUID image_id: Image identifier.
    :param str album_name: Album name.
    """
    execute_query(
        cql_queries.MOVE_IMAGE_TO_ALBUM,
        params=(album_name, image_id)
    )


def put_image_comment(image_id, user_id, comment):
    execute_query(
        cql_queries.COMMENT_IMAGE,
        params=(
            image_id,
            user_id,
            datetime.now(),
            comment,
        )
    )


def put_image_like(image_id, user_id):
    execute_query(
        cql_queries.LIKE_IMAGE,
        params=(
            image_id,
            user_id,
            datetime.now(),
        )
    )


def follow_user(follower_id, followee_id):
    execute_query(
        cql_queries.FOLLOW_USER,
        params=(follower_id, followee_id, datetime.now())
    )
