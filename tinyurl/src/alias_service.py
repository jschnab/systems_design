from fastapi import FastAPI

import postgres


class Batch:
    def __init__(self, size=1000):
        print("connecting to database")
        self.db = postgres.DB()
        self.size = size
        self.items = []
        self.load_batch()

    def load_batch(self):
        if len(self.items) > 0:
            return
        if self.db.con.closed:
            print("connecting to database")
            self.db.connect()
        print("getting new batch of aliases")
        self.items = postgres.get_aliases_batch(self.db.con, self.size)

    def get_alias(self):
        if len(self.items) == 0:
            self.load_batch()
        return self.items.pop()


app = FastAPI()
batch = Batch(1000)


@app.get("/get-alias")
def get_alias():
    return {"alias": batch.get_alias()}
