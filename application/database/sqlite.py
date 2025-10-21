import sqlite3
from sqlite3 import Error
from typing import Optional, Dict, Any
from logger.logger import setup_logger
from ._resources import current_timestamp


logger = setup_logger(__name__)


class SQLiteDBInit:
    """Initialize the SQLite database and create the necessary tables."""
    def __init__(self, db_file: str = "scraped_data.db") -> None:
        """
        Initialize the SQLiteDBInit instance.
        Args:
            db_file (str): The filename for the SQLite database. Defaults to 'scraped_data.db'.
        """
        self.db_file: str = db_file
        self.connection: Optional[sqlite3.Connection] = self.create_connection()
        self.create_product_table()

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

    def create_product_table(self) -> None:
        """
        Create the 'products' table in the database if it does not already exist.
        The table stores product information such as URL, title, price, description, images,
        name, company name, and category.
        Returns:
            None
        """
        try:
            if self.connection is not None:
                sql = '''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY,
                        url TEXT,
                        title TEXT,
                        price TEXT,
                        description TEXT,
                        images TEXT,
                        name TEXT,
                        company_name TEXT,
                        category TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );'''
                self.connection.execute(sql)
                self.connection.commit()
        except Error as e:
            print(f"Error creating table: {e}")


class ProductsCRUD:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn: sqlite3.Connection = connection
        # TODO: Get database name from database connection
    ######## *** CRUD 'products' operations *** ######
    def list_products(self) -> list:
        """List all products in the database
        Returns:
            list: A list of all products
        """
        products = []
        try:
            if not self.conn:
                logger.error(f'Error: Cannot connect to "{self}"')
                return products
            cur = self.conn.cursor()
            sql = f"""SELECT * FROM products"""
            cur.execute(sql)
            products = cur.fetchall()
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f'Cannot list products from products table: {e.__str__()}')
            print(f'Cannot list products from products table: {e.__str__()}')
        return products

    def get_product(self, product_id: int=0, url: str='') -> set:
        """Get product by product_id or url. If not found product or run into any problem return empty set
        Args:
            product_id (int): _description_
        Returns:
            set: _description_
        """
        try:
            product_data = set()
            if not self.conn:
                logger.error(f'Error: Cannot connect to sqldb')
                return product_data
            if not (product_id or url):
                logger.error(f'Error: product_id or url does not provided')
                return product_data
            cur = self.conn.cursor()
            if product_id:
                sql = f"""SELECT * FROM products WHERE id={product_id}"""
            elif url:
                sql = f"""SELECT * FROM products WHERE url={url}"""
            cur.execute(sql)
            product_data = cur.fetchone()
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f'Cannot get product data from products table: {e.__str__()}')
            print(f'\nCannot get product data from products table: {e.__str__()}')
        return product_data

    def insert_product(self, product_data: dict) -> bool:
        """Insert product data into the products table
        Returns:
            bool: _description_
        """
        try:
            if not self.conn:
                logger.error(f'Error: Cannot connect to sqldb')
                return False
            cur = self.conn.cursor()
            sql = f"""INSERT INTO products (
                url, title, price, description, images, company_name, created_at, updated_at
                )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);"""
            cur.execute(sql, (
                f"{product_data['url']}",
                f"{product_data['title']}",
                product_data['price'],
                f"{product_data['description']}",
                f"{product_data['images']}",
                f"{product_data['company_name']}",
                f"{current_timestamp()}",
                f"{current_timestamp()}"
            ))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f'Cannot insert product data into products table: {e.__str__()}')
            print(f'Cannot insert product data into products table: {e.__str__()}')
            return False
    
    def update_product(self, product_data: dict, product_id: int) -> bool:
        """Update products table using product_id
        Args:
            product_data (dict): _description_
            product_id (int): _description_
        Returns:
            bool: _description_
        """
        try:
            if not self.conn:
                logger.error(f'Error: Cannot connect to sqldb')
                return False
            cur = self.conn.cursor()
            sql = f'SELECT * FROM products WHERE id={product_id}'
            row = cur.execute(sql)
            product_data = row.fetchone()
            sql = f"""UPDATE products SET
                url = ?,
                title = ?,
                price = ?,
                description = ?,
                images = ?,
                company_name = ?,
                updated_at = ?
                WHERE id = {product_id};"""
            cur.execute(sql, (
                f"{product_data['url']}",
                f"{product_data['title']}",
                product_data['price'],
                f"{product_data['description']}",
                f"{product_data['images']}",
                f"{product_data['company_name']}",
                f"{current_timestamp()}",
            ))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f'Cannot update product data: {e.__str__()}')
            print(f'Cannot update product data: {e.__str__()}')
            return False

    def delete_product(self, product_id: int) -> bool:
        """Delete product row from products table using product_id
        Args:
            product_id (int): _description_
        Returns:
            bool: _description_
        """
        try:
            if not self.conn:
                logger.error(f'Error: Cannot connect to sqldb')
                return False
            cur = self.conn.cursor()
            sql = f'''DELETE FROM products WHERE id={product_id}'''
            cur.execute(sql)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f'Error in delete product ({product_id}): {e.__str__()}')
            print(f'Error in delete product ({product_id}): {e.__str__()}')
            return False
    ######## *** CRUD 'products' operations *** ######
