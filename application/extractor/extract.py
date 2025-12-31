"""
This module provides the Extractor class which can extract product information from e-commerce websites product pages.
It supports both Selenium and Requests methods for extraction, allowing flexibility based on the environment and requirements.
This module work on a single product page at a time.
"""

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from typing import Optional, Any
from application.driver.chrome import setup_driver
from application.data_management.manage_sqlite import upsert_product_data
from ._resources import (to_english_digits,
                        subset_dict,
                        clean_text,
                        process_price_text)
import requests
from requests import Response
import config
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
import time
from logger.logger import setup_logger
import json
import re


logger = setup_logger('scraper.log', __name__)


class Extractor:
    """This class is the hearth of the scraper application.\n
    It provides methods to extract product information from various e-commerce platforms using either Selenium or Requests libraries.\n"""
    def __init__(self, product_url: str, method: str=config.METHOD, driver: WebDriver|None=None, requests_response: Response|None=None, soup: BeautifulSoup|None=None, css_selectors: dict|None=None) -> None:
        # Initialize product attributes with default values one by one
        self.needed_fields: list = ['url', 'title', 'price', 'description', 'images', 'name', 'company_name', 'category']
        self.product_url = product_url
        self.product_title: str = 'N/A'
        self.product_price: int = 0
        self.product_description: str = 'N/A'
        self.product_images: list = []
        self.product_name: str = 'N/A'
        self.company_name: str = 'N/A'
        self.categories: list = []
        self.product_data: dict = {
            "url": self.product_url,
            "title": self.product_title,
            "price": self.product_price,
            "description": self.product_description,
            "images": self.product_images,
            "name": self.product_name,
            "company_name": self.company_name,
            "category": self.categories
        }
        self.driver: Optional[WebDriver] = driver
        self.requests_response: Optional[requests.Response] = requests_response
        self.html_body: str = ''
        self.soup = soup if soup else self.__initialize_soup()
        self.method = method
        self.css_selectors = css_selectors if css_selectors else {'title_selector': '', 'price_selector': '', 'description_selector': '', 'images_selector': '', 'company_selector': [], 'category_selector': ''}

    def scrape(self) -> dict:
        """
        Scraps and extract product data from a given e-commerce product URL. This is the main method of the Extractor class and start the extraction process.

        Args:
            url (str): The product page URL.

        Returns:
            dict: A dictionary containing product attributes such as title, price, description,
                images, name, company_name, category, and other standard product data.
        """
        try:
            # Following flag used to show if data extraction using orderly method was a success
            is_extraction_completed : bool = False
            logger.info(f'Product URL to be scrapped and extracted:\n{self.product_url}\n')
            # Call requests module first but if the URL should be loaded using Javascript then using Selenium to load the webpage
            if not self._call_requests_then_selenium():
                logger.error(f'\nDid not scraped product data from folowing webpage:\n{self.product_url}\n')
                return {'status': 'nok', 'msg': f'Could not scrapped data from {self.product_url}', 'data': {}}
            
            # ? Extract product data using different methods in order of reliability:
            
            # * 1) JSON-LD (structured)  2) Meta tags (og:, twitter:, product:)  3) DOM selectors
            logger.info('Try to scrape and extract product data using JSON-LD script...\n')
            json_ld_data = self._extract_json_ld_data(res) if (res := self._scrape_json_ld_script_tags()) else {}
            if json_ld_data:
                self.product_data = subset_dict(json_ld_data, self.needed_fields)
                logger.debug(f'\nAFTER EXTRACTION (JSON-LD): data extracted for webpage: "{self.product_url}":\n{self.product_data}')
                is_extraction_completed = True
                
            # *  2) If JSON-LD not available or incomplete, use meta tags first then DOM selectors to fill gaps
            if not is_extraction_completed:
                logger.info('Try to extract product data using Meta tags and DOM selectors...')
                meta = self._scrape_meta()
                # apply meta values where available
                if meta:
                    # simple fields
                    for f in ('title', 'description', 'name', 'company_name'):
                        if meta.get(f) and (not self.product_data.get(f) or self.product_data.get(f) in (None, '', 'N/A')):
                            self.product_data[f] = meta.get(f)
                    # price
                    if meta.get('price') and (not self.product_data.get('price')):
                        try:
                            price_val = meta.get('price')
                            if price_val:
                                self.product_data['price'] = int(price_val)
                        except Exception:
                            pass
                    # category
                    if meta.get('category') and (not self.product_data.get('category')):
                        self.product_data['category'] = meta.get('category')
                    # images - keep meta images to merge later with DOM images
                    meta_images = meta.get('images') or []
                else:
                    meta_images = []
                    
                # * 3) Use selectors to fill remaining fields
                selectors = self.css_selectors or {}
                extracted = self._extract_fields(
                    selectors.get('title_selector'),
                    selectors.get('price_selector'),
                    selectors.get('description_selector'),
                    selectors.get('images_selector'),
                    selectors.get('company_selector'),
                    selectors.get('category_selector')
                )
                # merge images: prefer meta images first, then DOM-extracted images, dedupe while preserving order
                final_images: list = []
                seen = set()
                for u in (meta_images + (extracted.get('images') or [])):
                    if not u:
                        continue
                    uu = str(u).strip()
                    if uu.startswith('//'):
                        uu = 'https:' + uu
                    uu = urljoin(self.product_url, uu) if not uu.startswith('data:') else uu
                    if uu in seen:
                        continue
                    seen.add(uu)
                    final_images.append(uu)
                self.product_data['images'] = final_images
                
            # ? Insert-upadte product data into database
            result: bool = upsert_product_data(product_data=self.product_data)
            if not result:
                logger.warning('No product inserted into/updated from product table')
            else:
                logger.info('Product data inserted/updated into product table')
        except Exception as e:
            logger.error(f'\nError happened in scraping data: {e.__str__()}\n')
            self._close_driver()
        if self.driver and not config.REUSE_DRIVER:
            self._close_driver()
        logger.debug(f'\nAFTER EXTRACTION: Web page URL is:\n"{self.product_url}\n"The extracted data in dict format:\n{self.product_data}\n')
        return {'status': 'ok', 'msg': 'Data scrapped and extracted with no error', 'data': self.product_data}

    # ! Following methods used to initialize Extraction instance
    
    def _call_requests_then_selenium(self) -> str|None:
        """If requests could not call website well use driver instead. If requests succeeded return 'requests' else call 'driver'. If non called the webpage return None. 
        """
        is_request_success = True
        if not self.__initialize_requests():
            logger.info('Cannot initialize requests')
            is_request_success = False
        # * Check if requests successfully 
        if not self.html_body:
            is_request_success = False
        if self.html_body and len(self.html_body) < 2000:
            logger.warning('Seems html requests is not loaded well')
            is_request_success = False
        if "enable javascript" in self.html_body.lower():
            logger.warning('JavaScript is required to load the page')
            is_request_success = False
        if self.soup and (self.soup.select_one('h1') is None or self.soup.select_one('h2') is None):
            logger.warning('The page must be loaded with selenium')
            is_request_success = False
        # * Load webpage using Selenium driver
        if not is_request_success:
            if not self.__initialize_driver():
                logger.error(f'Cannot load page even using Selenium in "{config.SLEEP_TIME}" seconds')
                return None
            logger.info('\nLoaded the page using selenium...\n')
            return 'selenium'
        logger.info('\nLoaded the webpage using requests...\n')
        return 'requests'
    
    def __initialize_driver(self) -> bool:
        """Initializes the Selenium WebDriver if not already done. If initialization fails, it returns False."""
        if not self.driver:
            self.driver = setup_driver()
        try:
            logger.info(f'Calling product page using selenium driver...')
            self.driver.get(self.product_url)
            time.sleep(config.SLEEP_TIME)  # Let JavaScript render
            self.html_body = self.driver.page_source
            self.__initialize_soup()
            return True
        except WebDriverException as e:
            logger.error(f"WebDriverException: {e}")
            self.driver.quit()
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.driver.quit()
        return False
    
    def __initialize_requests(self, header:dict={}) -> bool:
        """Initializes the requests response if not already done. If initialization fails, it returns False."""
        try:
            logger.info(f'Calling product page using requests module...')
            if not header:
                header['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0'
            response = requests.get(self.product_url, headers=header)
            response.raise_for_status()
            self.requests_response = response
            self.html_body = response.text
            self.__initialize_soup()
            return True
        except requests.RequestException as e:
            logger.error(f"RequestException: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return False
    
    def __initialize_soup(self) -> None:
        """Initializes the BeautifulSoup object if not already done. If initialization fails, it returns False."""
        try:
            self.soup = BeautifulSoup(self.html_body, "lxml")
        except Exception as e:
            self.soup = BeautifulSoup(self.html_body, "html.parser")

    def _close_driver(self) -> None:
        """Close selenium driver if exists"""
        try:
            if self.driver:
                logger.info('Closing selenium driver...')
                self.driver.quit()
        except Exception:
            pass
    
    # ! Following methods used to scrape data from web page using json+ld tag
    
    def _scrape_json_ld_script_tags(self) -> dict|None:
        """Scrape product data from JSON-LD script tags

        Returns:
            dict|None: Returns dict if data found in the 'ld+script' script tag. If no data found or error happened returns None.
        """
        try:
            if not self.soup:
                return
            json_ld_data = {}
            logger.info('Searching for application/ld+json script tags to scrape product data...')
            scripts = self.soup.find_all('script', type='application/ld+json')
            if not scripts:
                logger.warning('No application/ld+json script found')
                return
            for script in scripts:
                try:
                    json_content = script.text
                    if not json_content:
                        logger.warning('No json content found in the script')
                        return
                    # print (json_content)
                    if json_content:
                        data = json.loads(json_content)
                        if isinstance(data, list):
                            for item in data:
                                if item.get('@type') == 'Product':
                                    json_ld_data = item
                                    break
                        elif data.get('@type') == 'Product':
                            json_ld_data = data
                            break
                except Exception as e:
                    logger.error(f'Error parsing JSON-LD script: {e.__str__()}')
                    continue
            # Executed if found data in the script
            if json_ld_data:
                logger.info(f'Successfully scrapped JSON-LD script data:\n{json_ld_data}\n')
                return json_ld_data
            # If no data fround
            else:
                logger.warning('No JSON-LD data found\n')
        except Exception as e:
            logger.error(f'\nError in extracting data from JSON-LD: {e.__str__()}\n')
        return

    def _extract_json_ld_data(self, json_ld_data: dict) -> dict:
        """
        Extract structured product data from a JSON-LD Product dictionary.

        Args:
            json_ld_data (dict): The JSON-LD object returned from _scrape_json_ld() that
                describes a Product (or related objects).

        Returns:
            dict: Normalized product data ready for database upsert. Keys returned:
                - url (str)
                - title (str)
                - price (int)
                - description (str)
                - images (list[str])
                - name (str)       # same as title where applicable
                - company_name (str)
                - category (list[str])  # list for consistency
                - currency (str|None)
                - availability (str|None)
                - sku (str|None)
                - mpn (str|None)
                - rating (float|None)
                - review_count (int|None)
        """
        result: dict = {
            "url": self.product_url,
            "title": self.product_title,
            "price": 0,
            "description": self.product_description,
            "images": [],
            "name": self.product_name,
            "company_name": self.company_name,
            "category": [],
            "currency": None,
            "availability": None,
            "sku": None,
            "mpn": None,
            "rating": None,
            "review_count": None
        }
        try:
            if not json_ld_data or not isinstance(json_ld_data, dict):
                return result
            logger.info(f'\nExtracting data from scraped JSON-LD data that scrapped before...')
            # title / name
            title = json_ld_data.get("name") or json_ld_data.get("headline")
            if title:
                result["title"] = title
                result["name"] = title
            # description
            desc = json_ld_data.get("description")
            if desc:
                result["description"] = desc
            # images - can be string or list
            imgs = json_ld_data.get("image")
            if imgs:
                if isinstance(imgs, str):
                    result["images"] = [imgs]
                elif isinstance(imgs, (list, tuple)):
                    result["images"] = [str(i) for i in imgs if i]
            # brand / company name
            brand = json_ld_data.get("brand")
            if isinstance(brand, dict):
                result["company_name"] = brand.get("name") or result["company_name"]
            elif isinstance(brand, str):
                result["company_name"] = brand
            # category - normalize to list
            cat = json_ld_data.get("category")
            if cat:
                if isinstance(cat, str):
                    result["category"] = [cat]
                elif isinstance(cat, (list, tuple)):
                    result["category"] = [str(c) for c in cat if c]
            # identifiers
            sku = json_ld_data.get("sku")
            if sku:
                result["sku"] = str(sku)
            mpn = json_ld_data.get("mpn")
            if mpn:
                result["mpn"] = str(mpn)
            # ! Maybe needs works to be better
            # offers -> price, currency, availability
            offers = json_ld_data.get("offers")
            if offers:
                offer = offers[0] if isinstance(offers, list) and offers else offers
                if isinstance(offer, dict):
                    price_raw = offer.get("price") or offer.get("priceSpecification", {}).get("price")
                    currency = offer.get("priceCurrency") or offer.get("currency") or None
                    availability = offer.get("availability") or None
                    if price_raw is not None:
                        price_str = str(price_raw)
                        # convert any non-english digits
                        price_str = to_english_digits(price_str)
                        # remove non-digit/dot characters
                        price_str = re.sub(r"[^\d\.]", "", price_str)
                        try:
                            price_value = int(price_str) if price_str else 0
                            try:
                                if price_value and currency and currency.lower() in ('rial', 'ریال', 'irr'):
                                    price_value = price_value // 10
                            except (ValueError, TypeError, AttributeError):
                                pass
                            result["price"] = price_value
                        except Exception:
                            result["price"] = 0
                    result["currency"] = currency
                    result["availability"] = availability
            # aggregateRating
            agg = json_ld_data.get("aggregateRating") or {}
            if isinstance(agg, dict):
                rating_value = agg.get("ratingValue")
                review_count = agg.get("reviewCount")
                try:
                    result["rating"] = float(rating_value) if rating_value is not None else None
                except Exception:
                    result["rating"] = None
                try:
                    result["review_count"] = int(review_count) if review_count is not None else None
                except Exception:
                    result["review_count"] = None
        except Exception as e:
            logger.error(f"_extract_json_ld_data error: {e}")
        if result:
            logger.info(f'Successfully extracted JSON-LD data:\n{result}\n')
        else:
            logger.warning('No data extracted from JSON-LD')
        return result

    # ! Following methods used to scrape data from web page using og:<field> tag

    def _scrape_meta(self) -> dict:
        """Collect common meta tag fields into a dict for quick fallback access.

        Returns keys: title, description, images (list), price, company_name, category, name
        """
        try:
            if not self.soup:
                return {}
            result: dict = {}
            logger.info('Extracting data from meta tags...')
            # title / name
            title = self.__get_meta_content(['og:title', 'twitter:title'])
            if title:
                result['title'] = title
                result['name'] = title
                logger.info(f'Extracted title from meta tags: {title}')
                self.product_title = title
            # description
            desc = self.__get_meta_content(['og:description', 'twitter:description'])
            if desc:
                result['description'] = desc
                logger.info(f'Extracted description from meta tags: {desc}')
                self.product_description = desc
            # images - collect multiple if available
            images = []
            # property-based
            for key in ('og:image', 'og:image:secure_url', 'twitter:image', 'twitter:image:src'):
                v = self.__get_meta_content([key])
                if v:
                    images.append(v)
                    self.product_images.append(v)
            # link rel image_src
            tag = self.soup.find('link', rel='image_src')
            if tag and isinstance(tag, Tag) and tag.get('href'):
                images.append(str(tag.get('href')))
                self.product_images.append(str(tag.get('href')))
            # remove duplicates preserving order
            seen = set()
            images_clean = []
            for u in images:
                if not u:
                    continue
                uu = str(u).strip()
                if uu.startswith('//'):
                    uu = 'https:' + uu
                if not uu.startswith('data:'):
                    uu = urljoin(self.product_url, uu)
                if uu in seen:
                    continue
                seen.add(uu)
                images_clean.append(uu)
            if images_clean:
                logger.info(f'Extracted {len(images_clean)} images from meta tags')
                result['images'] = images_clean
            # price
            price = self.__get_meta_content(['product:price:amount', 'og:price:amount', 'price', 'og:price'])
            if price:
                price_candidate = process_price_text(str(price))
                if price_candidate > 0:
                    price = price_candidate
                result['price'] = price
                logger.info(f'Extracted price from meta tags: {price}')
                self.product_price = int(price)
            # company / site
            company = self.__get_meta_content(['og:site_name', 'author', 'brand', 'og:brand'])
            if company:
                result['company_name'] = company
                logger.info(f'Extracted company name from meta tags: {company}')
                self.company_name = company
            # category
            cat = self.__get_meta_content(['product:category', 'og:category', 'category'])
            if cat:
                parts = [p.strip() for p in re.split(r'[>,|;/\\]', str(cat)) if p.strip()]
                result['category'] = parts
                logger.info(f'Extracted category from meta tags: {parts}')
                self.categories = result['category']
            return result
        except Exception as e:
            logger.error(f'Error in extracting data from meta tags: {e.__str__()}\n')
            logger.error(f'Did not extract any data from meta tags\n')
            return {}

    def __get_meta_content(self, keys: list) -> str | None:
        """Return the first meta content for given property/name keys.

        Keys are tried in order; for each key we check `property` then `name` attributes.
        """
        try:
            if not self.soup:
                return None
            for key in keys:
                # try property
                tag = self.soup.find('meta', attrs={'property': key})
                if tag and isinstance(tag, Tag):
                    content = tag.get('content')
                    if content:
                        logger.info(f'Found meta tag for key "{key}": {content}')
                        return str(content).strip()
                # try name
                tag = self.soup.find('meta', attrs={'name': key})
                if tag and isinstance(tag, Tag):
                    content = tag.get('content')
                    if content:
                        logger.info(f'Found meta tag for key "{key}": {content}')
                        return str(content).strip()
            return None
        except Exception:
            return None
    
    # ! following methods used to scrape data for a single field
    
    def _extract_fields(self,
                        title_selector:str|list[str]|None=None,
                        price_selector:str|list[str]|None=None,
                        description_selector:str|list[str]|None=None,
                        images_selector:str|list[str]|None=None,
                        company_selector:str|list[str]|None=None,
                        category_selector:str|list[str]|None=None) -> dict:
        """Scrape and extract data for all needed fields one by one manually using css selectors

        Returns:
            dict: _description_
        """
        logger.info(f'Extact needed fields one by one...\n')
        self.product_title: str = self.__find_title(title_selector)
        self.product_price: int = self.__find_price(price_selector)
        self.product_description: str = self.__find_description(description_selector)
        self.product_images: list = self.__find_images(images_selector)
        self.product_name: str = self.product_title
        self.company_name: str = self.__find_company_name(company_selector)
        self.categories: list = self.__find_category(category_selector)
        self.product_data.update({
            "title": self.product_title,
            "price": self.product_price,
            "description": self.product_description,
            "images": self.product_images,
            "name": self.product_title,
            "company_name": self.company_name,
            "category": self.categories
        })
        logger.info('Extracting data for the fields one by one completed\n')
        return self.product_data
    
    def __find_title(self, title_selector: str|list|None=None) -> str:
        """Get product title
        """
        try:
            # If title is already founded in the product data from meta tags do not proceed to extract the title again
            if self.product_title:
                return self.product_title
            if not self.soup:
                return ''
            title: str = ''
            if isinstance(title_selector, str):
                title_selector = [title_selector]
            if not title_selector or not title:
                title_selector = ['h1', 'h2', '.product-title', '.product_name', '.product-name']
            if isinstance(title_selector, list):
                for selector in title_selector:
                    elements = self.soup.select(selector)
                    if elements:
                        title = elements[0].get_text().strip()
                        if title:
                            break
            if title:
                logger.info(f'Extracted title using DOM selectors: {title}')
            else:
                logger.info(f'Did not found title using DOM selectors without raising error')
        except Exception as e:
            logger.error(f'Error in getting product title: {e.__str__()}')
        return title
    
    def __find_price(self, price_selector: str|list|None=None) -> int:
        """Get product price
        """
        try:
            # If price is already founded in the product data from meta tags do not proceed to extract the price again
            if self.product_price:
                return self.product_price
            if not self.soup:
                return 0
            price: int = 0
            if not price_selector:
                price_selector = ['.price', '.product-price', '.amount', '.current-price', '.woocommerce-Price-amount', '.price-value', '.min-price']
            if isinstance(price_selector, str):
                price_selector = [price_selector]
            if isinstance(price_selector, list):
                for selector in price_selector:
                    elements = self.soup.select(selector)
                    # * If not found price elements using price selector use other methods
                    if not elements:
                        elements = self.soup.find_all('span', {'data-testid': 'price-final'})
                    if not elements:
                        elements = self.soup.find_all('span', {'data-testid': 'price-no-discount'})
                    if elements:
                        price_text: str = elements[0].get_text().strip()
                        price_value = process_price_text(price_text)
                        if price_value > 0:
                            price = price_value
            if price:
                logger.info(f'Extracted price using DOM selectors: {price}\n')
            else:
                logger.info(f'Did not found price using DOM selectors without raising error')
        except Exception as e:
            logger.error(f'Error in getting product price:\n{e.__str__()}\n')
        return price
    
    def __find_description(self, description_selector:str|list|None=None) -> str:
        """Get product description
        """
        try:
            # If description is already founded in the product data from meta tags do not proceed to extract the description again
            if self.product_description:
                return  self.product_description
            if not self.soup:
                return ''
            description: str = ''
            if not description_selector:
                description_selector = ['.description', '.product-description', '.describe']
            if isinstance(description_selector, str) and description_selector:
                description_selector = [description_selector]
            if isinstance(description_selector, list):
                for selector in description_selector:
                    elements = self.soup.select(selector)
                    if elements:
                        description = elements[0].get_text().strip()
                        if description:
                            break
            if description:
                logger.info(f'Extracted description using DOM selectors:\n{description}\n')
            else:
                logger.info(f'Did not found description using DOM selectors without raising error')
        except Exception as e:
            logger.error(f'Error in getting product description:\n{e.__str__()}\n')
        return description

    def __find_images(self, images_selector:str|list|None=None) -> list[str]:
        """Get product images
        """
        try:
            # If images is already founded in the product data from meta tags do not proceed to extract the images again
            if self.product_images:
                logger.info(f'Returning existing product_images ({len(self.product_images)} images)')
                return self.product_images
            if not self.soup:
                return []
            images: list[str] = []
            seen: set = set()
            # normalize selectors
            if not images_selector:
                selectors = ['.product-images img', '.product-gallery img', '.woocommerce-product-gallery__image img', '.gallery img', '.product-image img', 'img']
            elif isinstance(images_selector, str):
                selectors = [images_selector]
            else:
                selectors = images_selector
            def add_url(raw_url) -> None:
                if raw_url is None:
                    logger.info('add_url in extracting images: raw_url is None, skipping')
                    return
                u = str(raw_url).strip()
                if not u:
                    logger.info('add_url in extracting images: url empty after strip, skipping')
                    return
                # handle protocol-relative URLs
                if u.startswith('//'):
                    u = 'https:' + u
                # data URIs are fine as-is
                if not u.startswith('data:'):
                    u = urljoin(self.product_url, u)
                key = u
                # filter by extension or allow data URIs
                if not u.startswith('data:'):
                    if not re.search(r"\.(jpg|jpeg|png|webp|gif|svg|bmp|avif|ico)(?:[?#]|$)", u, re.I):
                        # allow some common image-like urls even without extension
                        if not re.search(r'/images?/|/img/|cdn|/uploads/|product', u, re.I):
                            logger.info(f'add_url in extracting images: url does not look like an image, skipping: {u}')
                            return
                if key in seen:
                    logger.info(f'add_url in extracting images: duplicate image URL skipped: {u}')
                    return
                seen.add(key)
                images.append(u)
            # extract from provided selectors
            for selector in selectors:
                try:
                    elements = self.soup.select(selector)
                except Exception:
                    elements = []
                for el in elements:
                    if isinstance(el, Tag):
                        if el.name == 'img':
                            src = el.get('src') or el.get('data-src') or el.get('data-original') or el.get('data-lazy-src')
                            # srcset handling - prefer highest-res candidate (last)
                            if (not src) and el.get('srcset'):
                                srcset_val = el.get('srcset')
                                srcset = str(srcset_val)
                                parts = [p.strip() for p in srcset.split(',') if p.strip()]
                                if parts:
                                    last = parts[-1].split()[0]
                                    src = last
                            if src is not None:
                                add_url(src)
                        else:
                            # anchor or other tag that may contain image link in href
                            href = el.get('href')
                            if href is not None:
                                add_url(href)
                            # inline style background-image
                            style = str(el.get('style') or '')
                            if style:
                                m = re.search(r'url\(([^)]+)\)', style)
                                if m:
                                    url_in_style = m.group(1).strip('\'\" ')
                                    add_url(url_in_style)
            if images:
                logger.info(f'Extracted {len(images)} images from DOM selectors\n')
            else:
                logger.info(f'Did not found images using DOM selectors without raising error')
        except Exception as e:
            logger.error(f'Error in getting product images:\n{e.__str__()}\n')
            logger.info('Returning empty images list due to exception\n')
        return images
    
    def __find_company_name(self, company_selector:str|list|None=None) -> str:
        """Get product company name
        """
        try:
            # If company name is already founded in the product data from meta tags do not proceed to extract the company name again
            if self.company_name:
                return self.company_name
            if not self.soup:
                return ''
            company_name: str = ''
            if not company_selector:
                company_selector = ['.brand', '.manufacturer', '.company-name', '.vendor']
            if isinstance(company_selector, str):
                company_selector = [company_selector]
            if isinstance(company_selector, list):
                for selector in company_selector:
                    elements = self.soup.select(selector)
                    if elements:
                        company_name = elements[0].get_text().strip()
                        if company_name:
                            break
            if company_name:
                logger.info(f'Extracted company name using DOM selectors: {company_name}\n')
            else:
                logger.info(f'Did not found company name using DOM selectors without raising error')
        except Exception as e:
            logger.error(f'Error in getting company name:\n{e.__str__()}\n')
        return company_name
    
    def __find_category(self, category_selector:str|list|None=None) -> list[str]:
        """Get product category
        """
        try:
            # If product category is already founded in the product data from meta tags do not proceed to extract the product category again
            if self.categories:
                return self.categories
            if not self.soup:
                return []
            categories: list[str] = []
            if not category_selector:
                category_selector = ['.category', '.product-category', '.tag', 'categories', '.breadcrumbs a', '.breadcrumb a']
            if isinstance(category_selector, str):
                category_selector = [category_selector]
            if isinstance(category_selector, list):
                for selector in category_selector:
                    elements = self.soup.select(selector)
                    if elements:
                        categories.extend([el.get_text().strip() for el in elements])
            if categories:
                logger.info(f'Extracted categories using DOM selectors: {categories}')
            else:
                logger.info(f'Did not found categories using DOM selectors')
        except Exception as e:
            logger.error(f'Error in getting product category:\n{e.__str__()}\n')
        return categories
