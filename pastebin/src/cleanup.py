from datetime import datetime

from . import cache
from . import database
from . import object_store


def cleanup():
    rows = database.get_texts_for_deletion()
    print(f"number of texts to cleanup: {len(rows)}")
    for row in rows:
        text_id = row["text_id"]
        print(f"cleaning up: {text_id}")
        print("deleting from object store")
        object_store.delete_text(text_id)
        print("deleting from cache")
        cache.delete(text_id)
        print("marking as deleted")
        database.mark_text_deleted(
            text_id=text_id, deletion_timestamp=datetime.now()
        )
        print(f"finished cleaning up: {text_id}")
    print("finished cleaning up all texts")


if __name__ == "__main__":
    cleanup()
