"""
This module provides an ecommerce product extractor for HTML product pages.
The Extractor class prioritizes structured JSON-LD and Open Graph metadata,
then uses generic DOM selectors as a fallback for WordPress/WooCommerce-style stores.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional, Any

import requests
from bs4 import BeautifulSoup, Tag
from requests import Response
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
from urllib.parse import urljoin

from application.driver.chrome import restart_driver, setup_driver
from application.data_management.manage_sqlite import upsert_product_data
from ._resources import clean_text, process_price_text
import config
from logger.logger import setup_logger

logger = setup_logger('scraper.log', __name__)


@dataclass
class ProductData:
    url: str
    title: str = ''
    price: int = 0
    description: str = ''
    images: list[str] = field(default_factory=list)
    name: str = ''
    company_name: str = ''
    category: list[str] = field(default_factory=list)
    currency: Optional[str] = None
    availability: Optional[str] = None
    sku: Optional[str] = None
    mpn: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'title': self.title,
            'price': self.price,
            'description': self.description,
            'images': self.images,
            'name': self.name or self.title,
            'company_name': self.company_name,
            'category': self.category,
            'currency': self.currency,
            'availability': self.availability,
            'sku': self.sku,
            'mpn': self.mpn,
            'rating': self.rating,
            'review_count': self.review_count,
        }


class Extractor:
    """Extract product information from an e-commerce product page."""

    DEFAULT_SELECTORS = {
        'title_selector': ['h1', 'h2', '.product-title', '.product_name', '.product-name'],
        'price_selector': [
            '.price', '.product-price', '.amount', '.current-price',
            '.woocommerce-Price-amount', '.price-value', '.min-price'
        ],
        'description_selector': ['.description', '.product-description', '.describe'],
        'images_selector': [
            '.product-images img', '.product-gallery img',
            '.woocommerce-product-gallery__image img', '.gallery img',
            '.product-image img', 'img'
        ],
        'company_selector': ['.brand', '.manufacturer', '.company-name', '.vendor'],
        'category_selector': ['.category', '.product-category', '.tag', 'categories', '.breadcrumbs a', '.breadcrumb a'],
    }

    def __init__(
        self,
        product_url: str,
        method: Optional[str] = None,
        driver: Optional[WebDriver] = None,
        requests_response: Optional[Response] = None,
        soup: Optional[BeautifulSoup] = None,
        css_selectors: Optional[dict] = None,
    ) -> None:
        self.product_url = product_url
        self.method = method or getattr(config, 'METHOD', 'requests')
        self.driver = driver
        self.requests_response = requests_response
        self.html_body = ''
        self.soup = soup
        self.css_selectors = css_selectors if css_selectors else {}
        self.product_data = ProductData(url=product_url)

    def scrape(self) -> dict:
        """Scrape product information from the provided product URL.
        This method attempts to fetch the product page using the specified method (requests or Selenium),
        then extracts product information using JSON-LD, meta tags, and CSS selectors.
        Returns:
            dict: A dictionary containing the scraping status, message, and extracted product data.
            Successful scrape returns {'status': 'ok', 'msg': 'Product scraped and stored successfully.', 'data': product_data_dict}.
            Failed scrape returns {'status': 'nok', 'msg': 'Error message', 'data
        """
        try:
            logger.info(f'Product URL to scrape: {self.product_url}')
            if not self._fetch_page():
                message = f'Failed to load product page: {self.product_url}'
                logger.error(message)
                return {'status': 'nok', 'msg': message, 'data': {}}
            # Scrape JSON-LD structured data first, then fallback to meta tags and CSS selectors
            json_ld_data = self._scrape_json_ld_script_tags()
            if json_ld_data:
                self._apply_json_ld(json_ld_data)
            meta_data = self._scrape_meta()
            self._apply_meta(meta_data)
            self._extract_fields(
                self.css_selectors.get('title_selector'),
                self.css_selectors.get('price_selector'),
                self.css_selectors.get('description_selector'),
                self.css_selectors.get('images_selector'),
                self.css_selectors.get('company_selector'),
                self.css_selectors.get('category_selector'),
            )
            # Ensure that the product name is set, defaulting to the title if not explicitly provided
            self.product_data.name = self.product_data.name or self.product_data.title
            # Store the scraped product data in the database
            stored = upsert_product_data(self.product_data.to_dict())
            if not stored:
                message = 'Scraped product data but failed to store in database.'
                logger.warning(message)
                return {'status': 'nok', 'msg': message, 'data': self.product_data.to_dict()}
            # Return the successfully scraped and stored product data
            return {'status': 'ok', 'msg': 'Product scraped and stored successfully.', 'data': self.product_data.to_dict()}
        except Exception as e:
            logger.error('Failed to scrape data')
            print(f'Error happened in scraping data: {e}')
            return {'status': 'nok', 'msg': 'Error in scraping data', 'data': {}}

    def _fetch_page(self) -> bool:
        # If the method is explicitly set to 'selenium', use Selenium to fetch the page.
        if self.method == 'selenium':
            return self.__initialize_driver()
        succeeded = self.__initialize_requests()
        if not succeeded or self._page_needs_js():
            logger.info('Falling back to Selenium for page rendering.')
            return self.__initialize_driver()
        return True

    def _page_needs_js(self) -> bool:
        if not self.html_body or not self.html_body.strip():
            return True
        # Check for common phrases indicating that JavaScript is required to view the content
        if 'enable javascript' in self.html_body.lower() or 'please enable javascript' in self.html_body.lower():
            return True
        if self.soup:
            has_json_ld = self.soup.find('script', type='application/ld+json') is not None
            if has_json_ld:
                return False
            if self.soup.find('h1') is None and self.soup.find('h2') is None:
                logger.warning('No page headings found; JavaScript may be required.')
                return True
        return False

    def __initialize_driver(self) -> bool:
        try:
            if not self.driver:
                self.driver = setup_driver()
            return self._load_with_driver()
        except WebDriverException as e:
            logger.warning(f'Selenium driver failed; restarting once: {e}')
            try:
                self.driver = restart_driver()
                return self._load_with_driver()
            except Exception as retry_error:
                logger.error(f'Selenium retry failed: {retry_error}')
                print(f'Selenium retry failed: {retry_error}')
                return False
        except Exception as e:
            logger.error('Error loading page with Selenium')
            print(f'Unexpected error loading page with Selenium: {e}')
            return False

    def _load_with_driver(self) -> bool:
        if not self.driver:
            return False
        self.driver.get(self.product_url)
        time.sleep(getattr(config, 'SLEEP_TIME', 3))
        self.html_body = self.driver.page_source
        self._initialize_soup()
        return True

    def _initialize_requests(self, header: dict | None = None) -> bool:
        return self.__initialize_requests(header)

    def __initialize_requests(self, header: dict | None = None) -> bool:
        """Initialize the requests session and fetch the product page.
        This method sets a default User-Agent header if none is provided, and uses the REQUEST_TIMEOUT from the config."""
        try:
            if header is None:
                header = {}
            header.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0')
            timeout = getattr(config, 'REQUEST_TIMEOUT', 10)
            response = requests.get(self.product_url, headers=header, timeout=timeout)
            response.raise_for_status()
            self.requests_response = response
            self.html_body = response.text
            self._initialize_soup()
            return True
        except requests.RequestException as e:
            logger.warning('Requests failed because requests timeout')
            print(f'Requests failed: {e}')
            return False
        except Exception as e:
            logger.warning('Unexpected error in initialize requests')
            print(f'Unexpected requests error: {e}')
            return False

    def _initialize_soup(self) -> bool:
        try:
            self.soup = BeautifulSoup(self.html_body, 'lxml')
            return True
        except Exception:
            self.soup = BeautifulSoup(self.html_body, 'html.parser')
            return bool(self.soup)

    def _close_driver(self) -> None:
        self.driver = None

    def _scrape_json_ld_script_tags(self) -> Optional[dict]:
        """Scrape JSON-LD structured data from <script type="application/ld+json"> tags in the HTML.
        This method looks for product data in JSON-LD format, which is commonly used for structured data on e-commerce sites"""
        if not self.soup:
            return None
        scripts = self.soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                json_text = script.get_text() or ''
                if not json_text.strip():
                    continue
                data = json.loads(json_text)
                product = self._find_product_json_ld(data)
                if product:
                    logger.info('Found JSON-LD product data.')
                    return product
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.warning('Error parsing JSON-LD script in product page')
                print(f'Error parsing JSON-LD script: {e}')
                continue
        return None

    def _find_product_json_ld(self, data: dict) -> Optional[dict]:
        """Recursively search for product data in JSON-LD structured data.
        This method checks for the presence of a product type in the JSON-LD data, and returns the corresponding dictionary if found. It handles nested structures and lists of JSON-LD objects.

        Args:
            data (Any): The JSON-LD data to search.

        Returns:
            Optional[dict]: The found product data or None.
        """
        if isinstance(data, dict):
            type_value = data.get('@type') or data.get('@type', '')
            if isinstance(type_value, list):
                if 'Product' in type_value:
                    return data
            if str(type_value).lower() == 'product':
                return data
            for key in ('mainEntity', 'itemListElement', 'graph'):
                if key in data:
                    candidate = self._find_product_json_ld(data[key])
                    if candidate:
                        return candidate
        elif isinstance(data, list):
            for item in data:
                candidate = self._find_product_json_ld(item)
                if candidate:
                    return candidate
        return None

    def _apply_json_ld(self, json_ld_data: dict) -> None:
        """Apply the extracted JSON-LD data to the product data.

        Args:
            json_ld_data (dict): The extracted JSON-LD data.
        """
        result = self._extract_json_ld_data(json_ld_data)
        self.product_data.title = result.get('title', self.product_data.title)
        self.product_data.price = result.get('price', self.product_data.price)
        self.product_data.description = result.get('description', self.product_data.description)
        self.product_data.images = result.get('images', self.product_data.images)
        self.product_data.name = result.get('name', self.product_data.name)
        self.product_data.company_name = result.get('company_name', self.product_data.company_name)
        self.product_data.category = result.get('category', self.product_data.category)
        self.product_data.currency = result.get('currency', self.product_data.currency)
        self.product_data.availability = result.get('availability', self.product_data.availability)
        self.product_data.sku = result.get('sku', self.product_data.sku)
        self.product_data.mpn = result.get('mpn', self.product_data.mpn)
        self.product_data.rating = result.get('rating', self.product_data.rating)
        self.product_data.review_count = result.get('review_count', self.product_data.review_count)

    def _extract_json_ld_data(self, json_ld_data: dict) -> dict:
        """ Extract relevant product information from JSON-LD structured data.

        Args:
            json_ld_data (dict): The extracted JSON-LD data.

        Returns:
            dict: A dictionary containing the extracted product information.
        """
        result = {
            'url': self.product_url,
            'title': '',
            'price': 0,
            'description': '',
            'images': [],
            'name': '',
            'company_name': '',
            'category': [],
            'currency': None,
            'availability': None,
            'sku': None,
            'mpn': None,
            'rating': None,
            'review_count': None,
        }
        if not isinstance(json_ld_data, dict):
            return result
        try:
            # Extract title, description, images, brand, category, offers, and aggregate rating from JSON-LD data
            title = json_ld_data.get('name') or json_ld_data.get('headline') or ''
            result['title'] = clean_text(str(title)) if title else ''
            result['name'] = result['title']
            result['description'] = clean_text(str(json_ld_data.get('description', '')))

            images = json_ld_data.get('image')
            if isinstance(images, str):
                result['images'] = [self._normalize_image(images)]
            elif isinstance(images, (list, tuple)):
                result['images'] = [self._normalize_image(img) for img in images if img]

            brand = json_ld_data.get('brand')
            if isinstance(brand, dict):
                result['company_name'] = clean_text(str(brand.get('name', '')))
            elif isinstance(brand, str):
                result['company_name'] = clean_text(brand)

            category = json_ld_data.get('category')
            if isinstance(category, str):
                result['category'] = [clean_text(category)]
            elif isinstance(category, (list, tuple)):
                result['category'] = [clean_text(str(c)) for c in category if c]

            offers = json_ld_data.get('offers')
            if offers:
                offer = offers[0] if isinstance(offers, list) else offers
                if isinstance(offer, dict):
                    price_raw = offer.get('price') or offer.get('priceSpecification', {}).get('price')
                    result['currency'] = offer.get('priceCurrency') or offer.get('currency')
                    result['availability'] = offer.get('availability')
                    if price_raw is not None:
                        result['price'] = process_price_text(str(price_raw))

            agg = json_ld_data.get('aggregateRating') or {}
            if isinstance(agg, dict):
                result['rating'] = self._safe_float(agg.get('ratingValue'))
                result['review_count'] = self._safe_int(agg.get('reviewCount'))
        except Exception as e:
            logger.warning('Error extracting JSON-LD data')
            print(f'Error extracting JSON-LD data: {e}')
        return result

    def _scrape_meta(self) -> dict:
        """Scrape Open Graph and Twitter Card metadata from the HTML head section.
        This method prioritizes Open Graph tags, then Twitter Card tags, and finally falls back to generic meta tags."""
        if not self.soup:
            self._initialize_soup()
        try:
            result: dict = {}
            title = self.__get_meta_content(['og:title', 'twitter:title'])
            if title:
                result['title'] = clean_text(title)
                result['name'] = clean_text(title)
                self.product_data.title = self.product_data.title or result['title']

            description = self.__get_meta_content(['og:description', 'twitter:description'])
            if description:
                result['description'] = clean_text(description)
                self.product_data.description = self.product_data.description or result['description']

            images = []
            for key in ('og:image', 'og:image:secure_url', 'twitter:image', 'twitter:image:src'):
                item = self.__get_meta_content([key])
                if item:
                    images.append(self._normalize_image(item))
            tag = self.soup.find('link', rel='image_src')
            if tag and isinstance(tag, Tag) and tag.get('href'):
                images.append(self._normalize_image(str(tag.get('href'))))
            if images:
                result['images'] = self._unique_urls(images)

            price_content = self.__get_meta_content(['product:price:amount', 'og:price:amount', 'price', 'og:price'])
            if price_content:
                result['price'] = process_price_text(str(price_content))
                self.product_data.price = self.product_data.price or result['price']

            company = self.__get_meta_content(['og:site_name', 'author', 'brand', 'og:brand'])
            if company:
                result['company_name'] = clean_text(company)
                self.product_data.company_name = self.product_data.company_name or result['company_name']

            category = self.__get_meta_content(['product:category', 'og:category', 'category'])
            if category:
                result['category'] = [clean_text(part) for part in re.split(r'[>,|;/\\]', category) if part.strip()]
                self.product_data.category = self.product_data.category or result['category']
        except Exception as e:
            logger.warning('Error scraping meta tags')
            print(f'Error scraping meta tags: {e}')
        return result

    def _apply_meta(self, meta_data: dict) -> None:
        """ Apply the extracted meta data to the product data, filling in any missing fields

        Args:
            meta_data (dict): The extracted meta data from the HTML head section.
        """
        if not meta_data:
            logger.info('No meta data found to apply.')
            return
        if meta_data.get('title') and not self.product_data.title:
            self.product_data.title = meta_data['title']
        if meta_data.get('description') and not self.product_data.description:
            self.product_data.description = meta_data['description']
        if meta_data.get('company_name') and not self.product_data.company_name:
            self.product_data.company_name = meta_data['company_name']
        if meta_data.get('category') and not self.product_data.category:
            self.product_data.category = meta_data['category']
        if meta_data.get('price') and not self.product_data.price:
            self.product_data.price = meta_data['price']
        if meta_data.get('images'):
            self.product_data.images = self._unique_urls(self.product_data.images + meta_data['images'])

    def __get_meta_content(self, keys: list[str]) -> str | None:
        """Retrieve the content of a meta tag based on a list of possible keys."""
        for key in keys:
            tag = self.soup.find('meta', attrs={'property': key})
            if tag and isinstance(tag, Tag) and tag.get('content'):
                return str(tag.get('content')).strip()
            tag = self.soup.find('meta', attrs={'name': key})
            if tag and isinstance(tag, Tag) and tag.get('content'):
                return str(tag.get('content')).strip()
        return None

    def _extract_fields(
        self,
        title_selector: str | list[str] | None = None,
        price_selector: str | list[str] | None = None,
        description_selector: str | list[str] | None = None,
        images_selector: str | list[str] | None = None,
        company_selector: str | list[str] | None = None,
        category_selector: str | list[str] | None = None,
    ) -> dict:
        """Extract product fields using CSS selectors, falling back to default selectors if none are provided."""
        title = self._find_title(title_selector)
        price = self._find_price(price_selector)
        description = self._find_description(description_selector)
        images = self._find_images(images_selector)
        company_name = self._find_company_name(company_selector)
        category = self._find_category(category_selector)

        if title and not self.product_data.title:
            self.product_data.title = title
        if price and not self.product_data.price:
            self.product_data.price = price
        if description and not self.product_data.description:
            self.product_data.description = description
        if images:
            self.product_data.images = self._unique_urls(self.product_data.images + images)
        if company_name and not self.product_data.company_name:
            self.product_data.company_name = company_name
        if category and not self.product_data.category:
            self.product_data.category = category

        return self.product_data.to_dict()

    def _find_title(self, title_selector: str | list[str] | None = None) -> str:
        if self.product_data.title:
            return self.product_data.title
        if not self.soup:
            return ''
        selectors = title_selector or self.DEFAULT_SELECTORS['title_selector']
        if isinstance(selectors, str):
            selectors = [selectors]
        for selector in selectors:
            try:
                elements = self.soup.select(selector)
            except Exception:
                elements = []
            if elements:
                text = elements[0].get_text().strip()
                if text:
                    return text
        return ''

    def _find_price(self, price_selector: str | list[str] | None = None) -> int:
        if self.product_data.price:
            return self.product_data.price
        if not self.soup:
            return 0
        selectors = price_selector or self.DEFAULT_SELECTORS['price_selector']
        if isinstance(selectors, str):
            selectors = [selectors]
        for selector in selectors:
            try:
                elements = self.soup.select(selector)
            except Exception:
                elements = []
            if not elements:
                elements = self.soup.find_all('span', {'data-testid': 'price-final'})
            if not elements:
                elements = self.soup.find_all('span', {'data-testid': 'price-no-discount'})
            if elements:
                raw = elements[0].get_text().strip()
                price = process_price_text(raw)
                if price > 0:
                    return price
        return 0

    def _find_description(self, description_selector: str | list[str] | None = None) -> str:
        if self.product_data.description:
            return self.product_data.description
        if not self.soup:
            return ''
        selectors = description_selector or self.DEFAULT_SELECTORS['description_selector']
        if isinstance(selectors, str):
            selectors = [selectors]
        for selector in selectors:
            try:
                elements = self.soup.select(selector)
            except Exception:
                elements = []
            if elements:
                text = elements[0].get_text().strip()
                if text:
                    return text
        return ''

    def _find_images(self, images_selector: str | list[str] | None = None) -> list[str]:
        if self.product_data.images:
            return self.product_data.images
        if not self.soup:
            return []
        selectors = images_selector or self.DEFAULT_SELECTORS['images_selector']
        if isinstance(selectors, str):
            selectors = [selectors]
        # Use a set to avoid duplicate image URLs
        images: list[str] = []
        for selector in selectors:
            try:
                elements = self.soup.select(selector)
            except Exception:
                elements = []
            for el in elements:
                if not isinstance(el, Tag):
                    continue
                if el.name == 'img':
                    raw = el.get('src') or el.get('data-src') or el.get('data-original') or el.get('data-lazy-src')
                    srcset = el.get('srcset')
                    # If the raw URL is not found, try to extract the last image URL from the srcset attribute
                    if not raw and srcset:
                        parts = [p.strip() for p in str(srcset).split(',') if p.strip()]
                        raw = parts[-1].split()[0] if parts else None
                    self._append_image(images, raw)
                else:
                    # For non-img elements, check for background images in the style attribute or href in anchor tags
                    href = el.get('href')
                    self._append_image(images, href)
                    style = str(el.get('style') or '')
                    if style:
                        match = re.search(r'url\(([^)]+)\)', style)
                        if match:
                            self._append_image(images, match.group(1).strip('"\' '))
        return images

    def _find_company_name(self, company_selector: str | list[str] | None = None) -> str:
        if self.product_data.company_name:
            return self.product_data.company_name
        if not self.soup:
            return ''
        selectors = company_selector or self.DEFAULT_SELECTORS['company_selector']
        if isinstance(selectors, str):
            selectors = [selectors]
        for selector in selectors:
            try:
                elements = self.soup.select(selector)
            except Exception:
                elements = []
            if elements:
                text = elements[0].get_text().strip()
                if text:
                    return text
        return ''

    def _find_category(self, category_selector: str | list[str] | None = None) -> list[str]:
        if self.product_data.category:
            return self.product_data.category
        if not self.soup:
            return []
        selectors = category_selector or self.DEFAULT_SELECTORS['category_selector']
        if isinstance(selectors, str):
            selectors = [selectors]
        categories: list[str] = []
        for selector in selectors:
            try:
                elements = self.soup.select(selector)
            except Exception:
                elements = []
            for el in elements:
                if isinstance(el, Tag):
                    categories.append(el.get_text().strip())
        return [clean_text(c) for c in categories if c]

    def _append_image(self, images: list[str], raw_url: Optional[str]) -> None:
        if not raw_url:
            return
        url = self._normalize_image(raw_url)
        if url and url not in images:
            images.append(url)

    def _normalize_image(self, raw_url: str) -> str:
        url = raw_url.strip()
        if url.startswith('//'):
            url = 'https:' + url
        if not url.startswith('data:'):
            url = urljoin(self.product_url, url)
        return url

    def _unique_urls(self, urls: list[str]) -> list[str]:
        seen = set()
        result: list[str] = []
        for url in urls:
            if not url:
                continue
            cleaned = url.strip()
            if cleaned in seen:
                continue
            seen.add(cleaned)
            result.append(cleaned)
        return result

    def _safe_int(self, value: Any) -> Optional[int]:
        try:
            return int(value)
        except Exception:
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None
