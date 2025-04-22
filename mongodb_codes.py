from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from bson.objectid import ObjectId
from datetime import datetime

class MongoDB_CRUD:
    def __init__(self, db_name='x_scraper', collection_name='users', host='localhost', port=27017):
        """
        Initialize MongoDB connection and collection
        """
        try:
            self.client = MongoClient(host, port)
            # The ismaster command is cheap and does not require auth
            self.client.admin.command('ismaster')
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            print("Connected to MongoDB successfully!")
        except ConnectionFailure as e:
            print(f"Could not connect to MongoDB: {e}")
            raise

    def create_document(self, data):
        """
        Create/Insert a new document
        """
        try:
            # Add timestamp if not provided
            if 'created_at' not in data:
                # data['created_at'] = datetime.utcnow()
                data['created_at'] = datetime.now()
            
            result = self.collection.insert_one(data)
            print(f"Document inserted with id: {result.inserted_id}")
            return result.inserted_id
        except DuplicateKeyError as e:
            print(f"Duplicate key error: {e}")
            return None
        except Exception as e:
            print(f"Error inserting document: {e}")
            return None

    def read_document(self, document_id):
        """
        Read a single document by ID
        """
        try:
            document = self.collection.find_one({'_id': ObjectId(document_id)})
            if document:
                print(f"Found document: {document}")
                return document
            else:
                print("No document found with that ID")
                return None
        except Exception as e:
            print(f"Error reading document: {e}")
            return None

    def read_all_documents(self, query={}, limit=0):
        """
        Read all documents matching query (empty query returns all)
        """
        try:
            documents = list(self.collection.find(query).limit(limit))
            print(f"Found {len(documents)} documents")
            return documents
        except Exception as e:
            print(f"Error reading documents: {e}")
            return None

    def update_document(self, document_id, update_data):
        """
        Update a document by ID
        """
        try:
            # Add updated_at timestamp
            # update_data['updated_at'] = datetime.utcnow()
            update_data['created_at'] = datetime.now()
            
            result = self.collection.update_one(
                {'_id': ObjectId(document_id)},
                {'$set': update_data}
            )
            if result.modified_count > 0:
                print(f"Successfully updated {result.modified_count} document(s)")
                return True
            else:
                print("No document was updated")
                return False
        except Exception as e:
            print(f"Error updating document: {e}")
            return False

    def delete_document(self, document_id):
        """
        Delete a document by ID
        """
        try:
            result = self.collection.delete_one({'_id': ObjectId(document_id)})
            if result.deleted_count > 0:
                print(f"Successfully deleted {result.deleted_count} document(s)")
                return True
            else:
                print("No document was deleted")
                return False
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    def close_connection(self):
        """
        Close MongoDB connection
        """
        self.client.close()
        print("MongoDB connection closed")


# Example usage
if __name__ == "__main__":
    # Initialize
    mongo_crud = MongoDB_CRUD(db_name='example_db', collection_name='users')
    
    # Create
    new_user = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'age': 30,
        'interests': ['python', 'mongodb', 'data science']
    }
    user_id = mongo_crud.create_document(new_user)
    
    # Read
    if user_id:
        user = mongo_crud.read_document(user_id)
        all_users = mongo_crud.read_all_documents()
    
    # Update
    if user_id:
        update_success = mongo_crud.update_document(user_id, {'age': 31, 'interests': ['python', 'mongodb', 'data science', 'AI']})
    
    # Delete
    # Uncomment to test delete functionality
    # if user_id:
    #     delete_success = mongo_crud.delete_document(user_id)
    
    # Close connection
    mongo_crud.close_connection()