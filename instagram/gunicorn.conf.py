import src.database


def post_fork(server, worker):
    server.log.info(f"Executing post-fork for worker {worker.pid}")
    src.database.configure_session()
