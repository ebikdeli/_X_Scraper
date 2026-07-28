"""
Insert or update product data extracted from e-commerce websites into SQLite database.
"""

from application.database.sqlite import SQLiteDB
from logger.logger import setup_logger
import config

logger = setup_logger('scraper.log', __name__)

def upsert_product_data(product_data: dict, db_file: str | None = None) -> bool:
    """
    Insert or update product data into the SQLite database.

    Args:
        product_data (dict): Dictionary containing product details.
        db_file (str | None): SQLite database file path. Defaults to config.DB_FILE.

    Returns:
        bool: True if the product was inserted or updated successfully.
    """
    logger.info("Try to insert or update data into database...")
    db_file = db_file or getattr(config, 'DB_FILE', 'scraped_data.db')
    try:
        db = SQLiteDB(db_file)
        return db.upsert_product(product_data)
    except Exception as e:
        logger.error("Error extracting and inserting product data into products")
        print(f"Error extracting and inserting product data into products: {e}")
        return False
