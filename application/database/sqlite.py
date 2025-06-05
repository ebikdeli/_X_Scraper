import sqlite3
from sqlite3 import Error

class SQLiteDB:
    def __init__(self, db_file="scraped_data.db"):
        self.db_file = db_file
        self.conn = self.create_connection()
        self.create_table()

    def create_connection(self):
        try:
            conn = sqlite3.connect(self.db_file)
            return conn
        except Error as e:
            print(f"Database connection error: {e}")
            return None

    def create_table(self):
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
            self.conn.execute(sql)
            self.conn.commit()
        except Error as e:
            print(f"Error creating table: {e}")

    def insert_data(self, product):
        try:
            sql = '''INSERT INTO products (url, title, price, description, images, name, company_name, category)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
            self.conn.execute(sql, (
                product.get("url"),
                product.get("title"),
                product.get("price"),
                product.get("description"),
                ",".join(product.get("images", [])),
                product.get("name"),
                product.get("company_name"),
                product.get("category")
            ))
            self.conn.commit()
        except Error as e:
            print(f"Error inserting data: {e}")
