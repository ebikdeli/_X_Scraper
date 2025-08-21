"""
Insert or Update product data extracted from e-commerce websites into SQLite database
"""

from application.database.sqlite import SQLiteDB
from application.extractor.extract import Extractor
from logger.logger import setup_logger


logger = setup_logger(__name__)


def insert_product_data(product_data: dict) -> bool:
    """
    Insert product data into the SQLite database. Return True if successful.
    Args:
        product_data (dict): Dictionary containing product details.
    """
    db = SQLiteDB()
    conn = db.create_connection()
    if conn is None:
        logger.error("Failed to create database connection.")
        return False
    cur = conn.cursor()
    try:
        # Assuming product_data contains a unique 'product_id'
        existing = cur.execute("SELECT * FROM products WHERE product_id = ?", (product_data['product_id'],)).fetchone()
        if existing:
            # Update existing record
            cur.execute(
                """
                UPDATE products SET name=?, price=?, stock=?, url=?, last_updated=DATETIME('now')
                WHERE product_id=?
                """,
                (
                    product_data.get('name'),
                    product_data.get('price'),
                    product_data.get('stock'),
                    product_data.get('url'),
                    product_data['product_id']
                )
            )
            logger.info(f"Updated product {product_data['product_id']}")
            return True 
        else:
            # Insert new record
            cur.execute(
                """
                INSERT INTO products (product_id, name, price, stock, url, last_updated)
                VALUES (?, ?, ?, ?, ?, DATETIME('now'))
                """,
                (
                    product_data.get('product_id'),
                    product_data.get('name'),
                    product_data.get('price'),
                    product_data.get('stock'),
                    product_data.get('url')
                )
            )
            logger.info(f"Inserted product {product_data['product_id']}")
            return True
    except Exception as e:
        logger.error(f"Error upserting product data: {e}")
    return False


def extract_and_upsert(url: str):
    """
    Extract product data from a URL and upsert into the database.
    Args:
        url (str): Product page URL.
    """
    extractor = Extractor(url)
    product_data = extractor.extract()
    if product_data:
        insert_product_data(product_data)
    else:
        logger.warning(f"No product data extracted from {url}")
