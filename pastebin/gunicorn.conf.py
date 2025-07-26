import asyncio

import src.cache
import src.database


def post_fork(server, worker):
    server.log.info(f"Executing post-fork for worker {worker.pid}")
    src.cache.init_connection_pool()
    src.database.init_thread_pool()
    src.database.init_connection_pool()


def worker_exit(server, worker):
    server.log.info(f"Cleaning up resources on worker {worker.pid}")
    asyncio.run(src.cache.close_connection_pool())
    src.database.close_thread_pool()
    src.database.close_connection_pool()
