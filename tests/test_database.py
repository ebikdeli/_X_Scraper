from core.database import SQLiteDB

def test_database_insert():
    db = SQLiteDB(":memory:")
    dummy_data = {
        "url": "http://example.com",
        "title": "Test Product",
        "price": "$9.99",
        "description": "Test Desc",
        "images": ["http://img.com/a.jpg"],
        "name": "Test Name",
        "company_name": "Test Co",
        "category": "Test Category"
    }
    db.insert_data(dummy_data)
