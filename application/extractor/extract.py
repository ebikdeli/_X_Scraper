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
from ._resources import to_english_digits, subset_dict, clean_text
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
        self.soup = soup
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
            is_extraction_completed : bool = False
            if not self._call_requests_then_selenium():
                logger.error(f'Cannot extract data from "{self.product_url}"')
                return {'status': 'nok', 'msg': f'Could not scrapped data from {self.product_url}', 'data': {}}
            logger.info(f'Product url to be extracted:\n{self.product_url}')
            # ? Extract product data using different methods in order of reliability:
            # * 1) JSON-LD (structured)  2) Meta tags (og:, twitter:, product:)  3) DOM selectors
            logger.info('Try to extract product data using JSON-LD script...')
            json_ld_data = self._extract_json_ld_data(res) if (res := self._scrape_json_ld()) else {}
            if json_ld_data:
                self.product_data = subset_dict(json_ld_data, self.needed_fields)
                logger.debug(f'\nAFTER EXTRACTION (JSON-LD): data extracted for: "{self.product_url}":\n{self.product_data}')
                result: bool = upsert_product_data(product_data=self.product_data)
                if not result:
                    logger.warning('No product inserted into/updated from product table')
                else:
                    logger.warning('Product data inserted/updated into product table')
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
                logger.warning('Product data inserted/updated into product table')
        except Exception as e:
            logger.error(f'\nError happened in scraping data: {e.__str__()}')
            self._close_driver()
        if self.driver and not config.REUSE_DRIVER:
            self._close_driver()
        logger.debug(f'\nAFTER EXTRACTION: data exracted for: "{self.product_url}":\n{self.product_data}')
        return {'status': 'ok', 'msg': 'Data scrapped and extracted successfully', 'data': self.product_data}

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
    
    def __initialize_soup(self) -> bool:
        """Initializes the BeautifulSoup object if not already done. If initialization fails, it returns False."""
        try:
            self.soup = BeautifulSoup(self.html_body, "html.parser")
            return True
        except requests.RequestException as e:
            logger.error(f"RequestException: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return False

    def _close_driver(self) -> None:
        """Close selenium driver if exists"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
    
    # ! Following methods used to scrape data from web page using json+ld tag
    
    def _scrape_json_ld(self) -> dict|None:
        """Extract product data from JSON-LD script tags

        Returns:
            dict|None: Returns dict if data found in the 'ld+script' script tag. If no data found or error happened returns None.
        """
        try:
            json_ld_data = {}
            if self.soup:
                # print('\n\nTO DEBUG...')
                # print('\n\n', self.soup.prettify(), '\n\n')
                # print('TO DEBUG\n\n')
                scripts = self.soup.find_all('script', type='application/ld+json')
                # print(scripts)
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
                            # print(type(data))
                            # print(data)
                            if isinstance(data, list):
                                for item in data:
                                    if item.get('@type') == 'Product':
                                        json_ld_data = item
                                        # break
                            elif data.get('@type') == 'Product':
                                json_ld_data = data
                                # break
                            return json_ld_data
                    except Exception as e:
                        logger.error(f'Error parsing JSON-LD script: {e.__str__()}')
        except Exception as e:
            logger.error(f'Error in extracting data from JSON-LD: {e.__str__()}')
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
                - price (float)
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
            "price": 0.0,
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
                            result["price"] = float(price_str) if price_str else 0.0
                        except Exception:
                            result["price"] = 0.0
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
            # title / name
            title = self._get_meta_content(['og:title', 'twitter:title'])
            if title:
                result['title'] = title
                result['name'] = title
                self.product_title = title
            # description
            desc = self._get_meta_content(['og:description', 'twitter:description'])
            if desc:
                result['description'] = desc
                self.product_description = desc
            # images - collect multiple if available
            images = []
            # property-based
            for key in ('og:image', 'og:image:secure_url', 'twitter:image', 'twitter:image:src'):
                v = self._get_meta_content([key])
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
                result['images'] = images_clean
            # price
            price = self._get_meta_content(['product:price:amount', 'og:price:amount', 'price', 'og:price'])
            if price:
                result['price'] = price
                self.product_price = int(price)
            # company / site
            company = self._get_meta_content(['og:site_name', 'author', 'brand', 'og:brand'])
            if company:
                result['company_name'] = company
                self.company_name = company
            # category
            cat = self._get_meta_content(['product:category', 'og:category', 'category'])
            if cat:
                parts = [p.strip() for p in re.split(r'[>,|;/\\]', str(cat)) if p.strip()]
                result['category'] = parts
                self.categories = result['category']
            return result
        except Exception:
            return {}

    def _get_meta_content(self, keys: list) -> str | None:
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
                        return str(content).strip()
                # try name
                tag = self.soup.find('meta', attrs={'name': key})
                if tag and isinstance(tag, Tag):
                    content = tag.get('content')
                    if content:
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
        """Scrape and extract data for all needed fields manually using css selectors

        Returns:
            dict: _description_
        """
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
        return self.product_data
    
    def __find_title(self, title_selector: str|list|None=None) -> str:
        """Get product title
        """
        try:
            if not self.soup:
                return ''
            if self.product_title:
                return self.product_title
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
            return title
        except Exception as e:
            logger.error(f'Error in getting product title: {e.__str__()}')
        return title
    
    def __find_price(self, price_selector: str|list|None=None) -> int:
        """Get product price
        """
        try:
            if self.product_price:
                return self.product_price
            if not self.soup:
                return 0
            price: int = 0
            # try meta price tags first
            meta_price = self._get_meta_content(['product:price:amount', 'og:price:amount', 'price', 'og:price'])
            if meta_price:
                try:
                    price_candidate = self.__process_price_text(str(meta_price))
                    if price_candidate > 0:
                        return price_candidate
                except Exception:
                    pass

            if not price_selector:
                price_selector = ['.price', '.product-price', '.amount', '.current-price', '.woocommerce-Price-amount', '.price-value']
            if isinstance(price_selector, str):
                price_selector = [price_selector]
            if isinstance(price_selector, list):
                for selector in price_selector:
                    elements = self.soup.select(selector)
                    if elements:
                        price_text: str = elements[0].get_text().strip()
                        price = self.__process_price_text(price_text)
                        if price > 0:
                            break
        except Exception as e:
            logger.error(f'Error in getting product price: {e.__str__()}')
        return price
    
    def __process_price_text(self, price_text: str) -> int:
        """Process and extract price from text string.
        
        Handles:
        - Converting non-English digits to English
        - Removing separator characters (dots, slashes, etc.)
        - Detecting ریال/rial and dividing by 10 if found
        
        Args:
            price_text: Raw price text extracted from HTML
            
        Returns:
            int: Processed price value
        """
        try:
            # Check if ریال or rial/Rial is present (case-insensitive for rial)
            has_rial = 'ریال' in price_text or 'rial' in price_text.lower()
            # Convert to English digits
            price_text = to_english_digits(price_text)
            # Remove all non-digit characters (removes separators like . / etc.)
            price_text = re.sub(r"[^\d]", "", price_text)
            # Convert to integer
            price = int(price_text) if price_text else 0
            # Divide by 10 if rial currency was detected
            if has_rial and price > 0:
                price = price // 10
            return price
        except Exception as e:
            logger.error(f'Error processing price text: {e.__str__()}')
            return 0
    
    def __find_description(self, description_selector:str|list|None=None) -> str:
        """Get product description
        """
        try:
            if self.product_description:
                return  self.product_description
            if not self.soup:
                return ''
            # try og:description / twitter:description first
            meta_desc = self._get_meta_content(['og:description', 'twitter:description'])
            if meta_desc:
                return meta_desc

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
            return description
        except Exception as e:
            logger.error(f'Error in getting product description: {e.__str__()}')
        return description

    def __find_images(self, images_selector:str|list|None=None) -> list[str]:
        """Get product images
        """
        try:
            if self.product_images:
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
                    return
                u = str(raw_url).strip()
                if not u:
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
                            return
                if key in seen:
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
            # also check common meta tags
            for mtag in self.soup.find_all('meta'):
                if not isinstance(mtag, Tag):
                    continue
                prop = str(mtag.get('property') or mtag.get('name') or '').lower()
                if prop in ('og:image', 'og:image:secure_url', 'twitter:image', 'twitter:image:src'):
                    content = mtag.get('content')
                    if content is not None:
                        add_url(content)
            return images
        except Exception as e:
            logger.error(f'Error in getting product images: {e.__str__()}')
        return []
    
    def __find_company_name(self, company_selector:str|list|None=None) -> str:
        """Get product company name
        """
        try:
            if self.company_name:
                return self.company_name
            if not self.soup:
                return ''
            # try og:site_name, author, brand meta tags first
            meta_company = self._get_meta_content(['og:site_name', 'author', 'brand', 'og:brand'])
            if meta_company:
                return meta_company

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
        except Exception as e:
            logger.error(f'Error in getting company name: {e.__str__()}')
        return company_name
    
    def __find_category(self, category_selector:str|list|None=None) -> list[str]:
        """Get product category
        """
        try:
            if self.categories:
                return self.categories
            if not self.soup:
                return []
            # try product:category / og:category meta tags first
            meta_cat = self._get_meta_content(['product:category', 'og:category', 'category'])
            if meta_cat:
                # split by common separators
                parts = [p.strip() for p in re.split(r'[>,|;/\\]', str(meta_cat)) if p.strip()]
                return parts

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
        except Exception as e:
            logger.error(f'Error in getting product category: {e.__str__()}')
        return categories
