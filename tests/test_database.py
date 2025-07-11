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
        self.mock_conn.execute.return_value = self.mock_cursor

    def test_create_connection_success(self):
        db = SQLiteDB("test.db")
        self.mock_connect.assert_called_with("test.db")
        self.assertEqual(db.conn, self.mock_conn)

    def test_create_connection_failure(self):
        # Patch to raise sqlite3.Error, which is what the code expects
        with patch("application.database.sqlite.sqlite3.connect", side_effect=Error("fail")):
            db = SQLiteDB("fail.db")
            self.assertIsNone(db.create_connection())

    def test_create_table_success(self):
        db = SQLiteDB("test.db")
        self.mock_conn.execute.assert_called()
        self.mock_conn.commit.assert_called()

    def test_create_table_failure(self):
        # Patch execute to raise sqlite3.Error, not Exception
        self.mock_conn.execute.side_effect = Error("table error")
        db = SQLiteDB("test.db")
        # Should print error, but not raise

    def test_insert_data_success(self):
        db = SQLiteDB("test.db")
        product = {
            "url": "http://a.com",
            "title": "Title",
            "price": "10",
            "description": "desc",
            "images": ["img1", "img2"],
            "name": "Name",
            "company_name": "Company",
            "category": "Cat"
        }
        db.insert_data(product)
        self.mock_conn.execute.assert_any_call(
            '''INSERT INTO products (url, title, price, description, images, name, company_name, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                "http://a.com", "Title", "10", "desc", "img1,img2", "Name", "Company", "Cat"
            )
        )
        self.mock_conn.commit.assert_called()

    def test_insert_data_failure(self):
        db = SQLiteDB("test.db")
        # Patch execute to raise sqlite3.Error, not Exception
        self.mock_conn.execute.side_effect = Error("insert error")
        product = {
            "url": "http://a.com",
            "title": "Title",
            "price": "10",
            "description": "desc",
            "images": ["img1", "img2"],
            "name": "Name",
            "company_name": "Company",
            "category": "Cat"
        }
        db.insert_data(product)
        # Should print error, but not raise
