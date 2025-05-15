import concurrent.futures
from core.logger import setup_logger
from core.database import SQLiteDB
from core.extractor import extract_product_data

logger = setup_logger()
db = SQLiteDB()

urls = [
    "https://example-woocommerce-site.com/product/sample-product-1",
    "https://example-woocommerce-site.com/product/sample-product-2"
]

def scrape_and_store(url):
    logger.info(f"Scraping URL: {url}")
    product = extract_product_data(url)
    if "error" not in product:
        db.insert_data(product)
        logger.info(f"Inserted data for: {url}")
    else:
        logger.error(f"Failed to scrape {url}: {product['error']}")

if __name__ == "__main__":
    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.map(scrape_and_store, urls)
