"""
This module handles the connection to MongoDB and saving or updating scraped product data.
# It uses the pymongo library to interact with MongoDB.
# It provides functions to get a MongoDB client and to save product data to the database.
"""


from pymongo import MongoClient

def get_db_client() -> MongoClient:
    """Return a MongoDB client instance."""
    return MongoClient("mongodb://localhost:27017/")

def save_to_mongodb(product, logger):
    """Insert or update the product document in MongoDB."""
    try:
        client = get_db_client()
        db = client["ecommerce_scraper"]
        products_collection = db["products"]
        products_collection.update_one(
            {"url": product["url"]},
            {"$set": product},
            upsert=True
        )
        logger.info(f"Saved product: {product['title']}")
    except Exception as e:
        logger.error(f"Error saving product {product.get('url', 'unknown')}: {e}")
    finally:
        client.close()
