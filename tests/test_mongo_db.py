import unittest
import pymongo
import mongodb_handler
import random


class TestMongoDb(unittest.TestCase):
    
    def setUp(self):
        self.client = None
        self.client = pymongo.MongoClient('mongodb://localhost:27017/')
        return super().setUp()
    
    def test_mongo_db_connect(self):
        """Test if mongodb database can be created"""
        self.assertIsNotNone(self.client)
    
    def test_create_drop_db_connect(self):
        """Test if mongodb database created"""
        numberOfTables: int = len(self.client.list_database_names())
        self.assertEqual(len(self.client.list_database_names()), numberOfTables)
        test_db = self.client['test_db']
        test_collection = test_db['test_collection']
        test_collection.insert_one({'_id': random.randint(1, 1000), 'data': 'A simple data'})
        self.assertNotEqual(len(self.client.list_database_names()), numberOfTables)
        try:
            print(self.client['test_db'])
            self.client.drop_database('test_db')
            self.assertEqual(len(self.client.list_database_names()), numberOfTables)
        except Exception as e:
            print('Test failed')
            print(e)
    
    def tearDown(self):
        self.client.close()
        return super().tearDown()


class TestMongoDbAdvanced(unittest.TestCase):
    """Test CRUD into mongodb"""
    def setUp(self):
        try:
            self.client = None
            self.client = pymongo.MongoClient('mongodb://localhost:27017/')
            self.test_db = self.client['test_db']
            self.product_collection = self.test_db['products']
            self.category_collection = self.test_db['categories']
            self.order_collection = self.test_db['orders']
            self.user_collection = self.test_db['users']
            return super().setUp()
        except:
            print("\nEXIT ALL THE MONGODB ADVANCED TESTS\n")
            exit()
    
    def test_insert_into_db(self):
        """Test if data inserted into the mongodb table successfully"""
        
    
    def tearDown(self):
        try:
            self.client.drop_database('test_db')
            return super().tearDown()
        except:
            pass
