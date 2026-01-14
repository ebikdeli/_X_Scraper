import concurrent.futures
from logger.logger import setup_logger
from application.extractor.robots_parser import start_extract_robots_links
from application.extractor.extract import Extractor


# logger = setup_logger('scraper.log', __name__)
logger = setup_logger('scraper.log', '_main')


def scrape_and_store(base_website:str|None=None, product_urls: str|list[str]|tuple[str]|set[str]|None=None) -> None:
    """Extract and store product data from 'base_website' or 'product_urls'.

    Args:
        base_website (str | None, optional): base website to extract robots.txt from. This arguement is more important than 'product_urls'. Defaults to None.
        product_urls (str | list[str] | tuple[str] | set[str] | None, optional): _description_. Defaults to None.
    """
    if not base_website and not product_urls:
        logger.error('both of base website and product_urls cannot be empty at the same time')
    if base_website:
        product_urls = start_extract_robots_links(base_website)
    product_extracted: int = 0
    if not product_urls:
        logger.warning('No product url found')
    elif isinstance(product_urls, str):
        url = product_urls.strip().replace('\n', '').replace('\t', '')
        url = "".join(url.split())
        logger.info(f"Scraping URL: {url}")
        extractor = Extractor(url)
        product = extractor.scrape()
        product_extracted += 1
    elif isinstance(product_urls, list) or isinstance(product_urls, tuple) or isinstance(product_urls, set):
        for url in product_urls:
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
    # product_url = """https://datkala.com/product/%d9%84%d9%be-%d8%aa%d8%a7%d9%be-%d9%84%d9%86%d9%88%d9%88-15-6-%d8%a7%db%8c%d9%86%da%86%db%8c-%d9%85%d8%af%d9%84-loq-i7-14700hx-32gb-512gb-rtx-5060/"""
    product_url = """https://kookmobile.com/product/samsung-galaxy-a16-mobile-128gb-4gb-ram/"""
    # product_url: str = 'https://www.digikala.com/product/dkp-20805124/%D9%84%D9%BE-%D8%AA%D8%A7%D9%BE-16-%D8%A7%DB%8C%D9%86%DA%86%DB%8C-%D8%A7%DB%8C%D8%B3%D9%88%D8%B3-%D9%85%D8%AF%D9%84-vivobook-16-r1605va-mb994-i3-1315u-8gb-ddr4-3200mhz-512gb-ssd-ips/?variant_id=73896923'

    scrape_and_store(product_urls=product_url)


main()

# if __name__ == "__main__":
#     with concurrent.futures.ProcessPoolExecutor() as executor:
#         executor.map(scrape_and_store, urls)
