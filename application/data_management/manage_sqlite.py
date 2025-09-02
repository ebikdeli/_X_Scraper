"""
Insert or Update product data extracted from e-commerce websites into SQLite database
"""

from application.database.sqlite import SQLiteDBInit, ProductsCRUD
from application.extractor.extract import Extractor
from logger.logger import setup_logger
import sqlite3


logger = setup_logger(__name__)


def upsert_product_data(product_data: dict, db_connection: sqlite3.Connection|None=None, update: bool=False, url: str='') -> bool:
    """
    Insert or update product data into the SQLite database. By default try to insert every product data found into database but if update argument is True, if the url currently is in the database try to update the data instead of inserting data. Returns True if successful.
    Args:
        product_data (dict): Dictionary containing product details.
    """
    try:
        conn = db_connection
        if not conn:
            db = SQLiteDBInit()
            conn = db.connection
            if conn is None:
                logger.error("Failed to create database connection.")
                return False
        if update:
            # TODO update product data
            pass
        else:
            # Insert new record into products
            pd = ProductsCRUD(conn)
            if pd.insert_product(product_data):
                logger.info(f"Inserted product: {product_data}")
                return True
        logger.warning(f"Failed to insert product: {product_data}")
    except Exception as e:
        logger.error(f"Error extract and inserting product data into products: {e}")
    return False


def extract_and_upsert(url: str):
    """
    Extract product data from a URL and insert into the database.
    Args:
        url (str): Product page URL.
    """
    extractor = Extractor(url)
    product_data = extractor.extract()
    if product_data:
        upsert_product_data(product_data)
    else:
        logger.warning(f"No product data extracted from {url}")
