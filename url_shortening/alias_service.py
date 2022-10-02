from fastapi import FastAPI

import database


class Batch:
    def __init__(self, size=1000):
        print("connecting to database")
        self.con = database.connect()
        self.size = size
        self.items = []
        self.load_batch()

    def load_batch(self):
        if len(self.items) > 0:
            return
        if self.con.closed:
            print("connecting to database")
            self.con = database.connect()
        print("getting new batch of aliases")
        self.items = database.get_aliases_batch(self.con, self.size)

    def get_alias(self):
        if len(self.items) == 0:
            self.load_batch()
        return self.items.pop()


app = FastAPI()
batch = Batch(10)


@app.get("/get-alias")
def get_alias():
    return {"alias": batch.get_alias()}
