import argparse
import sys
from logger.logger import setup_logger
import config
from application.extractor.extract import Extractor
from application.extractor.robots_parser import start_extract_robots_links

logger = setup_logger('scraper.log', __name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='MVP ecommerce scraper for Iranian WordPress/WooCommerce storefronts.'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--product-url',
        nargs='+',
        help='One or more product page URLs to scrape.',
    )
    group.add_argument(
        '--site-url',
        help='Base website URL to scan robots.txt and sitemap locations for product pages.',
    )
    parser.add_argument(
        '--method',
        choices=['requests', 'selenium'],
        default=config.METHOD,
        help='Fetch method to use for scraping. Selenium is more reliable for JS-driven pages.',
    )
    parser.add_argument(
        '--db-file',
        default=getattr(config, 'DB_FILE', 'scraped_data.db'),
        help='SQLite database file to store scraped products.',
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run Selenium in headless mode when using --method selenium.',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show debug output while scraping.',
    )
    return parser


def scrape_urls(urls: list[str], method: str) -> int:
    total = 0
    success_count = 0
    for url in urls:
        url = url.strip()
        if not url:
            continue
        total += 1
        logger.info(f'Scraping product URL: {url}')
        extractor = Extractor(product_url=url, method=method)
        result = extractor.scrape()
        if result.get('status') == 'ok':
            success_count += 1
            logger.info(f'Successfully scraped: {url}')
        else:
            logger.warning(f'Failed to scrape: {url} - {result.get("msg")}')
    return success_count


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel('DEBUG')

    if args.headless:
        config.SELENIUM_HEADLESS = True

    config.DB_FILE = args.db_file
    product_urls = []
    if args.site_url:
        logger.info(f'Scanning robots.txt and sitemaps for {args.site_url}')
        product_urls = start_extract_robots_links(args.site_url, method=args.method)
        if not product_urls:
            logger.error('No product URLs were found in sitemaps.')
            return 1
    elif args.product_url:
        product_urls = args.product_url

    success = scrape_urls(product_urls, args.method)
    logger.info(f'Scraped {success}/{len(product_urls)} product URLs.')
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
