import unittest
import pymongo
import mongodb_handler


class TestMongoDb(unittest.TestCase):
    
    def setUp(self):
        self.client = pymongo.MongoClient('mongodb://localhost:27017/')
        return super().setUp()
    
    def test_mongo_db_connect(self):
        """Test if mongodb database can be created"""
        for ld in self.client.list_databases():
            print(ld)
    
    def tearDown(self):
        self.client.close()
        return super().tearDown()
        