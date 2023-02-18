from datetime import datetime

from cassandra.cluster import (
    Cluster,
    ExecutionProfile,
    EXEC_PROFILE_DEFAULT,
)
from cassandra.query import named_tuple_factory
from cassandra.util import SortedSet

from . import cql_queries
from . import return_codes
from .config import CONFIG


def configure_session():
    profile = ExecutionProfile(
        consistency_level=CONFIG["database"].getint(
            "default_consistency_level"
        ),
        request_timeout=CONFIG["database"].getint("default_request_timeout"),
        row_factory=named_tuple_factory,
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


def rows_to_dicts(rows):
    return tuple(row._asdict() for row in rows)


def create_table_users():
    execute_query(cql_queries.CREATE_TABLE_USERS)


def create_table_user_follows():
    execute_query(cql_queries.CREATE_TABLE_USER_FOLLOWS)


def create_table_user_is_followed():
    execute_query(cql_queries.CREATE_TABLE_USER_FOLLOWED)


def create_table_images_by_user():
    execute_query(cql_queries.CREATE_TABLE_IMAGES_BY_USER)


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
    create_table_user_follows()
    create_table_user_is_followed()
    create_table_images()
    create_table_images_by_user()
    create_table_albums()
    create_table_image_comments()
    create_table_image_likes()


def create_user(user_id, first_name, last_name, password):
    response = execute_query(
        cql_queries.CREATE_USER,
        params=(
            user_id,
            first_name,
            last_name,
            password,
            datetime.now(),
        ),
    )
    if not response[0].applied:
        return return_codes.USER_EXISTS
    return return_codes.OK


def add_image(
    image_id,
    image_description,
    owner_id,
    tags,
    album_name,
):
    now = datetime.now()
    execute_query(
        cql_queries.INSERT_IMAGE_BY_USER,
        params=(
            owner_id,
            now,
            image_id,
            f"{CONFIG['image_store']['s3_bucket']}/{image_id}",
        ),
    )
    execute_query(
        cql_queries.INSERT_IMAGE,
        params=(
            image_id,
            f"{CONFIG['image_store']['s3_bucket']}/{image_id}",
            owner_id,
            now,
            image_description,
            tags,
        ),
    )
    if album_name is not None:
        add_image_to_album(image_id, album_name, owner_id)


def get_image_info(image_id):
    response = execute_query(
        cql_queries.GET_IMAGE_INFO, params=(image_id,)
    )
    if len(response) > 0:
        return rows_to_dicts(response)[0]


def tag_image(image_id, tags):
    execute_query(cql_queries.TAG_IMAGE, params=(tags, image_id))


def create_album(album_name, user_id):
    execute_query(
        cql_queries.ADD_ALBUM_TO_USER, params=(album_name, user_id)
    )
    response = execute_query(
        cql_queries.CREATE_ALBUM, params=(album_name, user_id, datetime.now())
    )
    if not response[0].applied:
        return return_codes.ALBUM_EXISTS
    return return_codes.OK


def follow_user(follower_id, followed_id):
    now = datetime.now()
    execute_query(
        cql_queries.INSERT_USER_FOLLOWS,
        params=(follower_id, followed_id, now),
    )
    execute_query(
        cql_queries.INSERT_USER_FOLLOWED,
        params=(followed_id, follower_id, now),
    )


def add_image_to_album(image_id, album_name, user_id):
    execute_query(
        cql_queries.SET_ALBUM_FOR_IMAGE,
        params=(album_name, image_id),
    )
    execute_query(
        cql_queries.ADD_IMAGE_TO_ALBUM,
        params=(image_id, album_name, user_id),
    )


def comment_image(image_id, user_id, comment_text):
    execute_query(
        cql_queries.COMMENT_IMAGE,
        params=(
            image_id,
            datetime.now(),
            user_id,
            comment_text,
        ),
    )


def like_image(image_id, user_id):
    execute_query(
        cql_queries.LIKE_IMAGE,
        params=(image_id, datetime.now(), user_id),
    )


def get_followed_users(user_id):
    response = execute_query(
        cql_queries.GET_FOLLOWED_USERS, params=(user_id,)
    )
    return tuple(row.followed_id for row in response)


def get_follower_users(user_id):
    response = execute_query(
        cql_queries.GET_FOLLOWER_USERS, params=(user_id,)
    )
    return rows_to_dicts(response)


def get_images_by_user(user_id):
    response = execute_query(
        cql_queries.GET_IMAGES_BY_USER,
        params=(user_id,),
    )
    return rows_to_dicts(response)


def get_image_comments(image_id):
    response = execute_query(
        cql_queries.GET_IMAGE_COMMENTS, params=(image_id,)
    )
    return rows_to_dicts(response)


def get_image_likes(image_id):
    response = execute_query(cql_queries.GET_IMAGE_LIKES, params=(image_id,))
    return rows_to_dicts(response)


def get_user_info(user_id):
    response = execute_query(cql_queries.GET_USER_INFO, params=(user_id,))
    if len(response) == 0:
        return {}
    return rows_to_dicts(response)[0]


def get_albums_by_user(user_id):
    response = execute_query(cql_queries.GET_ALBUMS_BY_USER, params=(user_id,))
    if len(response) == 0:
        return SortedSet()
    return response[0].album_names or SortedSet()


def get_album_info(album_name, owner_id):
    response = execute_query(
        cql_queries.GET_ALBUM_INFO, params=(album_name, owner_id)
    )
    if len(response) == 0:
        return {}
    return rows_to_dicts(response)[0]


def user_is_locked(user_id):
    return False


def record_user_connect(user_id, user_ip, success):
    pass
