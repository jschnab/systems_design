from datetime import datetime, timedelta

from cassandra.cluster import (
    Cluster,
    ExecutionProfile,
    EXEC_PROFILE_DEFAULT,
    NoHostAvailable,
)
from cassandra.query import dict_factory
from cassandra.util import SortedSet

from . import cql_queries
from . import return_codes
from .config import CONFIG
from .logging import BASE_LOGGER

LOGGER = BASE_LOGGER.getChild(__name__)
MAX_CONNECT_FAIL = 3
USER_LOCK_TIMEOUT = 15
CLUSTER = None
SESSION = None


class PreparedStatements:
    ready = False


def configure_cluster():
    global CLUSTER
    LOGGER.info("Configuring Cassandra execution profile")
    profile = ExecutionProfile(
        consistency_level=CONFIG["database"].getint(
            "default_consistency_level"
        ),
        request_timeout=CONFIG["database"].getint("default_request_timeout"),
        row_factory=dict_factory,
    )
    LOGGER.info("Configuring Cassandra cluster info")
    CLUSTER = Cluster(
        CONFIG["database"]["endpoints"].split(","),
        port=CONFIG["database"]["port"],
        execution_profiles={EXEC_PROFILE_DEFAULT: profile},
    )
    LOGGER.info("Finished configuring cluster info")


def configure_session():
    global SESSION
    LOGGER.info("Configuring Cassandra session")
    keyspace = CONFIG["database"]["keyspace_name"]
    try:
        configure_cluster()
        LOGGER.info(f"Connecting using keyspace '{keyspace}'")
        SESSION = CLUSTER.connect(keyspace)
    # NoHostAvailable is raised if the keyspace does not exist.
    except NoHostAvailable:
        LOGGER.info("Failed to connect using keyspace '{keyspace}'")
        # Reusing the cluster object after a failed connection leads to a
        # 'NoHostAvailable' exception.
        configure_cluster()
        LOGGER.info("Connecting using default keyspace")
        SESSION = CLUSTER.connect()
    LOGGER.info("Connected to Cassandra cluster")
    # By default a tuple is converted to a list, leading to errors when some
    # queries are parsed.
    SESSION.encoder.mapping[tuple] = SESSION.encoder.cql_encode_tuple
    LOGGER.info("Finished configuring Cassandra session")


def prepare_statements():
    LOGGER.info("Preparing CQL statments")
    if SESSION is None:
        configure_session()
    for var in dir(cql_queries):
        if var.endswith("_QRY"):
            setattr(
                PreparedStatements,
                var.replace("_QRY", ""),
                SESSION.prepare(getattr(cql_queries, var)),
            )
    PreparedStatements.ready = True
    LOGGER.info("Finished preparing CQL statements")


def execute_query(query, params=None):
    if SESSION is None:
        configure_session()
    return SESSION.execute(query, params).all()


def create_keyspace():
    LOGGER.info("Creating keyspace")
    config = CONFIG["database"]
    execute_query(
        cql_queries.CREATE_KEYSPACE.format(keyspace=config["keyspace_name"]),
        params=(config["replication_class"], config["replication_factor"]),
        prepared=False,
    )
    LOGGER.info(f"Finished creating keyspace {config['keyspace_name']}")


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


def create_table_user_connections():
    execute_query(cql_queries.CREATE_TABLE_USER_CONNECTIONS)


def create_table_image_popularity():
    execute_query(cql_queries.CREATE_TABLE_IMAGE_POPULARITY)


def create_table_user_feeds():
    execute_query(cql_queries.CREATE_TABLE_USER_FEEDS)


def create_tables():
    LOGGER.info("Creating tables")
    create_table_users()
    create_table_user_follows()
    create_table_user_is_followed()
    create_table_images()
    create_table_images_by_user()
    create_table_albums()
    create_table_image_comments()
    create_table_image_likes()
    create_table_user_connections()
    create_table_image_popularity()
    create_table_user_feeds()
    LOGGER.info("Finished creating tables")


def create_user(user_id, first_name, last_name, password):
    response = execute_query(
        PreparedStatements.CREATE_USER,
        params=(
            user_id,
            first_name,
            last_name,
            password,
            datetime.now(),
            {CONFIG["general"]["default_album_name"]},
        ),
    )
    if not response[0]["[applied]"]:
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
        PreparedStatements.INSERT_IMAGE_BY_USER,
        params=(
            owner_id,
            album_name,
            now,
            image_id,
            f"{CONFIG['image_store']['s3_bucket']}/{image_id}",
        ),
    )
    execute_query(
        PreparedStatements.INSERT_IMAGE,
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
        PreparedStatements.GET_IMAGE_INFO, params=(image_id,)
    )
    if len(response) > 0:
        return response[0]


def tag_image(image_id, tags):
    execute_query(PreparedStatements.TAG_IMAGE, params=(tags, image_id))


def create_album(album_name, user_id):
    execute_query(
        PreparedStatements.ADD_ALBUM_TO_USER, params=({album_name}, user_id)
    )
    response = execute_query(
        PreparedStatements.CREATE_ALBUM,
        params=(album_name, user_id, datetime.now()),
    )
    if not response[0]["[applied]"]:
        return return_codes.ALBUM_EXISTS
    return return_codes.OK


def follow_user(follower_id, followed_id):
    now = datetime.now()
    execute_query(
        PreparedStatements.INSERT_USER_FOLLOWS,
        params=(follower_id, followed_id, now),
    )
    execute_query(
        PreparedStatements.INSERT_USER_FOLLOWED,
        params=(followed_id, follower_id, now),
    )


def add_image_to_album(image_id, album_name, user_id):
    execute_query(
        PreparedStatements.SET_ALBUM_FOR_IMAGE,
        params=(album_name, image_id),
    )
    execute_query(
        PreparedStatements.ADD_IMAGE_TO_ALBUM,
        params=({image_id}, album_name, user_id),
    )


def comment_image(image_id, user_id, comment_text):
    execute_query(
        PreparedStatements.COMMENT_IMAGE,
        params=(
            image_id,
            datetime.now(),
            user_id,
            comment_text,
        ),
    )


def like_image(image_id, user_id):
    execute_query(
        PreparedStatements.LIKE_IMAGE,
        params=(image_id, user_id, datetime.now()),
    )


def get_followed_users(user_id):
    response = execute_query(
        PreparedStatements.GET_FOLLOWED_USERS, params=(user_id,)
    )
    return tuple(row["followed_id"] for row in response)


def get_follower_users(user_id):
    response = execute_query(
        PreparedStatements.GET_FOLLOWER_USERS, params=(user_id,)
    )
    return response


def get_images_by_user(user_id):
    response = execute_query(
        PreparedStatements.GET_IMAGES_BY_USER,
        params=(user_id,),
    )
    return response


def get_image_comments(image_id):
    response = execute_query(
        PreparedStatements.GET_IMAGE_COMMENTS, params=(image_id,)
    )
    return response


def get_image_likes(image_id):
    response = execute_query(
        PreparedStatements.GET_IMAGE_LIKES, params=(image_id,)
    )
    return response


def get_image_like_by_user(image_id, user_id):
    response = execute_query(
        PreparedStatements.GET_IMAGE_LIKE_BY_USER, params=(image_id, user_id)
    )
    if len(response) > 0:
        return response[0]


def get_user_info(user_id):
    response = execute_query(
        PreparedStatements.GET_USER_INFO, params=(user_id,)
    )
    if len(response) == 0:
        return {}
    return response[0]


def get_albums_by_user(user_id):
    response = execute_query(
        PreparedStatements.GET_ALBUMS_BY_USER, params=(user_id,)
    )
    if len(response) == 0:
        return SortedSet()
    return response[0]["album_names"] or SortedSet()


def get_album_info(album_name, owner_id):
    response = execute_query(
        PreparedStatements.GET_ALBUM_INFO, params=(album_name, owner_id)
    )
    if len(response) == 0:
        return {}
    return response[0]


def get_album_images(album_name, owner_id):
    response = execute_query(
        PreparedStatements.GET_ALBUM_IMAGES, params=(owner_id, album_name)
    )
    if len(response) == 0:
        return []
    return response


def user_is_locked(user_id):
    timestamp = datetime.now() - timedelta(minutes=15)
    result = execute_query(
        PreparedStatements.GET_RECENT_USER_CONNECTIONS,
        params=(user_id, timestamp),
    )
    connections = result
    if len(connections) < MAX_CONNECT_FAIL:
        return False
    failures = 0
    for con in connections:
        if con["success"]:
            break
        failures += 1
    last_connection_time = connections[0]["connection_timestamp"]
    lock_cutoff = datetime.now() - timedelta(minutes=USER_LOCK_TIMEOUT)
    if failures >= MAX_CONNECT_FAIL and last_connection_time > lock_cutoff:
        return True
    return False


def record_user_connect(user_id, user_ip, success):
    execute_query(
        PreparedStatements.RECORD_USER_CONNECTION,
        params=(
            user_id,
            datetime.now(),
            user_ip,
            success,
        ),
    )


def count_user_images_by_album_timestamp(user_id, album_names, timestamp):
    if not isinstance(album_names, tuple):
        album_names = tuple(album_names)
    return execute_query(
        PreparedStatements.COUNT_USER_IMAGES_BY_ALBUM_TIMESTAMP,
        params=(user_id, album_names, timestamp),
    )[0]["count"]


def increment_image_popularity(image_id):
    execute_query(
        PreparedStatements.INCREMENT_IMAGE_POPULARITY, params=(image_id,)
    )


def get_image_popularity(image_id):
    result = execute_query(
        PreparedStatements.GET_IMAGE_POPULARITY, params=(image_id,)
    )
    if result == []:
        return 0
    return result[0]["popularity"]


def user_exists(user_id):
    return (
        execute_query(PreparedStatements.USER_EXISTS, params=(user_id,)) != []
    )


def get_user_images_by_album_timestamp(user_id, album_names, timestamp):
    if not isinstance(album_names, tuple):
        album_names = tuple(album_names)
    result = execute_query(
        PreparedStatements.GET_USER_IMAGES_BY_ALBUM_TIMESTAMP,
        params=(user_id, album_names, timestamp),
    )
    return result


def get_followers():
    result = execute_query(PreparedStatements.GET_FOLLOWERS)
    return result


def insert_feed_images(n_records, params):
    query = (
        "BEGIN BATCH "
        f"{PreparedStatements.INSERT_USER_FEED * n_records} "
        "APPLY BATCH"
    )
    execute_query(query, params)


def get_user_feed(user_id):
    return execute_query(PreparedStatements.GET_USER_FEED, params=(user_id,))
