import unittest
from unittest.mock import patch, MagicMock
from sqlite3 import Error
from application.database.sqlite import SQLiteDB


class TestSQLiteDB(unittest.TestCase):
    def setUp(self):
        patcher = patch("application.database.sqlite.sqlite3.connect")
        self.addCleanup(patcher.stop)
        self.mock_connect = patcher.start()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connect.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

    def test_create_connection_success(self):
        db = SQLiteDB("test.db")
        self.mock_connect.assert_called_with("test.db", check_same_thread=False)
        self.assertEqual(db.connection, self.mock_conn)

    def test_create_connection_failure(self):
        with patch("application.database.sqlite.sqlite3.connect", side_effect=Error("fail")):
            db = SQLiteDB("fail.db")
            self.assertIsNone(db.connection)

    def test_create_table_success(self):
        SQLiteDB("test.db")
        self.mock_conn.execute.assert_called()
        self.mock_conn.commit.assert_called()

    def test_create_table_failure(self):
        self.mock_conn.execute.side_effect = Error("table error")
        db = SQLiteDB("test.db")
        self.assertIsNotNone(db.connection)
        self.mock_conn.execute.assert_called()
        self.mock_conn.commit.assert_not_called()

    def test_upsert_product_success(self):
        db = SQLiteDB("test.db")
        product = {
            "url": "http://a.com",
            "title": "Title",
            "price": 10,
            "description": "desc",
            "images": ["img1", "img2"],
            "name": "Name",
            "company_name": "Company",
            "category": ["Cat"],
            "currency": "USD",
            "availability": "InStock",
            "sku": "SKU123",
            "mpn": "MPN123",
            "rating": 4.5,
            "review_count": 10,
        }
        self.mock_cursor.execute.return_value = None
        result = db.upsert_product(product)
        self.assertTrue(result)
        self.mock_cursor.execute.assert_called()
        self.mock_conn.commit.assert_called()

    def test_upsert_product_missing_url(self):
        db = SQLiteDB("test.db")
        product = {"title": "No URL"}
        result = db.upsert_product(product)
        self.assertFalse(result)

    def test_upsert_product_failure(self):
        db = SQLiteDB("test.db")
        self.mock_cursor.execute.side_effect = Error("insert error")
        product = {
            "url": "http://a.com",
            "title": "Title",
            "price": 10,
            "description": "desc",
            "images": ["img1"],
            "name": "Name",
            "company_name": "Company",
            "category": ["Cat"],
        }
        result = db.upsert_product(product)
        self.assertFalse(result)
