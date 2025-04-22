import unittest
import pymongo
import mongodb_handler
import random
from bson.objectid import ObjectId
from mongodb_codes import MongoDB_CRUD


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
        product_data = {'name': 'samsung', 'price': 1234343}
        self.product_collection.insert_one(product_data)
        self.assertEqual(self.product_collection.count_documents({}), 1)
        self.assertEqual(self.product_collection.find_one({'name': 'samsung'})['price'], 1234343)
    
    def test_update_db(self):
        """Test if data updated the mongodb table successfully"""
        product_data = {'name': 'samsung', 'price': 1234343}
        self.product_collection.insert_one(product_data)
        self.product_collection.update_one({'name': 'samsung'}, {'$set': {'price': 999999}})
        self.assertEqual(self.product_collection.find_one({'name': 'samsung'})['price'], 999999)
    
    def test_delete_from_db(self):
        """Test if data deleted from the mongodb table successfully"""
        product_data = {'name': 'samsung', 'price': 1234343}
        self.product_collection.insert_one(product_data)
        self.product_collection.delete_one({'name': 'samsung'})
        self.assertEqual(self.product_collection.count_documents({}), 0)

    def test_read_from_db(self):
        """Test if data read from the mongodb table successfully"""
        product_data = {'name': 'samsung', 'price': 1234343}
        self.product_collection.insert_one(product_data)
        result = self.product_collection.find_one({'name': 'samsung'})
        self.assertIsNotNone(result)
        self.assertEqual(result['price'], 1234343)
    
    def tearDown(self):
        try:
            self.client.drop_database('test_db')
            self.client.close()
            return super().tearDown()
        except:
            pass


class TestMongoDBCRUD(unittest.TestCase):
    def setUp(self):
        """
        Set up a test database and collection for testing.
        """
        self.test_db_name = "test_db"
        self.test_collection_name = "test_collection"
        self.mongo_crud = MongoDB_CRUD(db_name=self.test_db_name, collection_name=self.test_collection_name)
        print('\n')
        
    def test_create_document(self):
        """
        Test the create_document method.
        """
        data = {"name": "Test User", "email": "test@example.com"}
        inserted_id = self.mongo_crud.create_document(data)
        self.assertIsNotNone(inserted_id)
        document = self.mongo_crud.read_document(inserted_id)
        self.assertEqual(document["name"], "Test User")
        self.assertEqual(document["email"], "test@example.com")
        print('\n')

    def test_read_document(self):
        """
        Test the read_document method.
        """
        data = {"name": "Read Test", "email": "read@example.com"}
        inserted_id = self.mongo_crud.create_document(data)
        document = self.mongo_crud.read_document(inserted_id)
        self.assertIsNotNone(document)
        self.assertEqual(document["_id"], ObjectId(inserted_id))
        self.assertEqual(document["name"], "Read Test")
        print('\n ')

    def test_read_all_documents(self):
        """
        Test the read_all_documents method.
        """
        self.mongo_crud.create_document({"name": "User 1"})
        self.mongo_crud.create_document({"name": "User 2"})
        documents = self.mongo_crud.read_all_documents()
        self.assertEqual(len(documents), 2)
        print('\n')

    def test_update_document(self):
        """
        Test the update_document method.
        """
        data = {"name": "Update Test", "email": "update@example.com"}
        inserted_id = self.mongo_crud.create_document(data)
        update_data = {"email": "updated@example.com"}
        update_success = self.mongo_crud.update_document(inserted_id, update_data)
        self.assertTrue(update_success)
        updated_document = self.mongo_crud.read_document(inserted_id)
        self.assertEqual(updated_document["email"], "updated@example.com")
        print('\n')

    def test_delete_document(self):
        """
        Test the delete_document method.
        """
        data = {"name": "Delete Test", "email": "delete@example.com"}
        inserted_id = self.mongo_crud.create_document(data)
        delete_success = self.mongo_crud.delete_document(inserted_id)
        self.assertTrue(delete_success)
        deleted_document = self.mongo_crud.read_document(inserted_id)
        self.assertIsNone(deleted_document)
        print('\n')

    def tearDown(self):
        """
        Tear down the test database after testing.
        """
        self.mongo_crud.client.drop_database(self.test_db_name)
        self.mongo_crud.close_connection()
