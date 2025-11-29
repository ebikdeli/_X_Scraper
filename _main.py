import concurrent.futures
from logger.logger import setup_logger
from application.extractor.extract import Extractor

# logger = setup_logger('scraper.log', __name__)
logger = setup_logger('scraper.log', '_main')

urls = [
    "https://example-woocommerce-site.com/product/sample-product-1",
    "https://example-woocommerce-site.com/product/sample-product-2"
]


def scrape_and_store(urls: str|list[str]|tuple[str]|set[str]) -> None:
    """Start scraping data from url(s)"""
    product_extracted: int = 0
    if not urls:
        logger.warning('No product url found')
    elif isinstance(urls, str):
        url = urls.strip().replace('\n', '').replace('\t', '')
        url = "".join(url.split())
        logger.info(f"Scraping URL: {url}")
        extractor = Extractor(url)
        product = extractor.scrape()
        product_extracted += 1
    elif isinstance(urls, list) or isinstance(urls, tuple) or isinstance(urls, set):
        for url in urls:
            if isinstance(url, str):
                url = url.strip().replace('\n', '').replace('\t', '')
                url = "".join(url.split())
                logger.info(f"Scraping URL: {url}")
                extractor = Extractor(product_url=url)
                product = extractor.scrape()
                product_extracted += 1
    if "error" not in product:
        logger.info(f"Data inserted-updated for the URL(s) successfully")
    else:
        logger.error(f"Failed to scrape data for the URL(s)")


def main():
    product_url = """https://datkala.com/product/%d9%84%d9%be-%d8%aa%d8%a7%d9%be-%d9%84%d9%86%d9%88%d9%88-15-6-%d8%a7%db%8c%d9%86%da%86%db%8c-%d9%85%d8%af%d9%84-loq-i7-14700hx-32gb-512gb-rtx-5060/"""
    scrape_and_store(product_url)


main()

# if __name__ == "__main__":
#     with concurrent.futures.ProcessPoolExecutor() as executor:
#         executor.map(scrape_and_store, urls)
