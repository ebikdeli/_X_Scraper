import sqlite3
from sqlite3 import Error
from typing import Optional, Dict, Any

class SQLiteDB:
    """
    A simple SQLite database handler for storing and managing product data.

    This class provides methods to connect to an SQLite database, create a products table,
    and insert product records. It is designed for use in web scraping or data collection
    applications where structured product information needs to be persisted.
    """

    def __init__(self, db_file: str = "scraped_data.db") -> None:
        """
        Initialize the SQLiteDB instance.

        Args:
            db_file (str): The filename for the SQLite database. Defaults to 'scraped_data.db'.
        """
        self.db_file: str = db_file
        self.conn: Optional[sqlite3.Connection] = self.create_connection()
        self.create_table()

    def create_connection(self) -> Optional[sqlite3.Connection]:
        """
        Establish a connection to the SQLite database.

        Returns:
            Optional[sqlite3.Connection]: The database connection object if successful, otherwise None.
        """
        try:
            conn = sqlite3.connect(self.db_file)
            return conn
        except Error as e:
            print(f"Database connection error: {e}")
            return None

    def create_table(self) -> None:
        """
        Create the 'products' table in the database if it does not already exist.

        The table stores product information such as URL, title, price, description, images,
        name, company name, and category.

        Returns:
            None
        """
        try:
            sql = '''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY,
                        url TEXT,
                        title TEXT,
                        price TEXT,
                        description TEXT,
                        images TEXT,
                        name TEXT,
                        company_name TEXT,
                        category TEXT
                    );'''
            if self.conn is not None:
                self.conn.execute(sql)
                self.conn.commit()
            else:
                print("No database connection. Table creation skipped.")
        except Error as e:
            print(f"Error creating table: {e}")

