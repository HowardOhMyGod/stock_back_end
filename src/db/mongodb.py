from pymongo import MongoClient
import pymongo.errors as mongoError
import os

class Mongo:
    def __init__(self):
        pass

    @staticmethod
    def connect(db, client =None):
        '''Return db object'''

        if not client:
            client = os.environ['local_db']


        client = MongoClient(client)

        try:
            client.admin.command('ismaster')

        except mongoError.ConnectionFailure:
            raise ConnectionError(db, client)

        else:
            return client[db]

    @staticmethod
    def is_in_collection(collection, query):
        return collection.find(query).count() > 0



class MongoError(Exception):
    def __init__(self, db, client = None):
        super().__init__(db, client)
        self.db = db
        self.client = client

class ConnectionError(MongoError):
    pass


