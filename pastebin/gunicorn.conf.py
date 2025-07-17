import src.cache
import src.database


def post_fork(server, worker):
    server.log.info(f"Executing post-fork for worker {worker.pid}")
    src.cache.init_connection_pool()
    src.database.init_thread_pool()
    src.database.init_connection_pool()
