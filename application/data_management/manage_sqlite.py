"""
Insert or Update product data extracted from e-commerce websites into SQLite database.
"""

from application.database.sqlite import SQLiteDBInit, ProductsCRUD
from logger.logger import setup_logger
import sqlite3


logger = setup_logger(__name__)


def upsert_product_data(product_data: dict, db_connection: sqlite3.Connection|None=None, update: bool=False, url: str='') -> bool:
    """
    Insert or update product data into the SQLite database. By default try to insert every product data found into database but if update argument is True, if the url currently is in the database try to update the data instead of inserting data. Returns True if successful.
    Args:
        product_data (dict): Dictionary containing product details.
    """
    print("Try to insert-update data into database...")
    try:
        conn = db_connection
        if not conn:
            db = SQLiteDBInit()
            conn = db.connection
            if conn is None:
                # logger.error("Failed to create database connection.")
                print("\nFailed to create database connection.")
                return False
        pd = ProductsCRUD(conn)
        if update:
            product_set: set = pd.get_product(url=product_data['url'])
            product_list: list = list(product_set)
            if product_set:
                if pd.update_product(product_data, product_list[1]):
                    # logger.info(f'product_id({product_list[0]}) updated')
                    print(f'product_id({product_list[0]}) updated')
        else:
            # Insert new record into products
            if pd.insert_product(product_data):
                # logger.info(f"Inserted new product: {product_data}")
                print(f"Inserted new product: {product_data}")
                return True
        # logger.warning(f"Failed to insert product into products table")
        print(f"Failed to insert product into products table")
    except Exception as e:
        # logger.error(f"Error extract and inserting product data into products: {e}")
        print(f"Error extract and inserting product data into products: {e}")
    return False
