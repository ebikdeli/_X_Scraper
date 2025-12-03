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
import time
from logger.logger import setup_logger
import json
import re


logger = setup_logger('scraper.log', __name__)


class Extractor:
    """A class to extract product data from e-commerce websites.\n
    Every methods that scrape a single attribute can be called with arbitrary scraping method (For eg, we can scrape title with selenium and image using Beautiful soup. But beware because it could have additional proccessing overhead).\n"""
    def __init__(self, product_url: str, method: str=config.METHOD, driver: WebDriver|None=None, requests_response: Response|None=None, soup: BeautifulSoup|None=None):
        # Initialize product attributes with default values one by one
        self.needed_fields: list = ['url', 'title', 'price', 'description', 'images', 'name', 'company_name', 'category']
        self.product_url = product_url
        self.product_title: str = 'N/A'
        self.product_price: float = 0.0
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

    def scrape(self) -> dict:
        """
        Scraps and extract product data from a given e-commerce product URL.

        Args:
            url (str): The product page URL.

        Returns:
            dict: A dictionary containing product attributes such as title, price, description,
                images, name, company_name, category, and other standard product data.
        """
        try:
            is_extracted_completed : bool = False
            if config.METHOD == "selenium":
                if not self._initialize_driver():
                    return {'status': 'error', 'msg': 'WebDriverException occurred', 'data': self.product_data}
            elif config.METHOD == "requests":
                if not self._initialize_soup():
                    return {'status': 'error', 'msg': 'RequestException occurred', 'data': self.product_data}
            logger.info(f'Product url to be extracted:\n{self.product_url}')
            # ? Extract product data using diffrent methods
            # * 1- Extract data using "script-json+ld tag". If json_ld script tag found in the web page return the product_data
            json_ld_data = self._extract_json_ld_data(res) if (res := self._scrape_json_ld()) else {}
            if json_ld_data:
                self.product_data = subset_dict(json_ld_data, self.needed_fields)
                logger.debug(f'\nAFTER EXTRACTION: data exracted for: "{self.product_url}":\n{self.product_data}')
                # ? Insert-upadte product data into database
                result: bool = upsert_product_data(product_data=self.product_data)
                if not result:
                    logger.warning('No product inserted into/updated from product table')
                else:
                    logger.warning('Product data inserted/updated into product table')
                is_extracted_completed = True
            # * 2- Extract data using "generic field value" if not found in JSON-LD (The problem with this method is this method is very inaqurate and its success rate is lower than 10%)
            # if not is_extracted_completed:
            # self.product_data = {
            #     "url": self.product_url,
            #     "title": self._get_generic_field_value('title', '', css_selector='h1'),
            #     "price": self._get_generic_field_value('price', 0, css_selector='.woocommerce-Price-amount'),
            #     "description": self._get_generic_field_value('description', '', css_selector='.woocommerce-product-details__short-description'),
            #     "images": self._get_generic_field_value('images', [], css_selector='.woocommerce-product-gallery__image img', multi_value=True),
            #     "company_name": self._get_generic_field_value('company_name', '', css_selector='.brand, .manufacturer'),
            #     "category": self._get_generic_field_value('category', '', css_selector='.posted_in a'),
            # }
            # * 3- If any Product data field could not be found in previous methods try to scrape data using single fields
            if not is_extracted_completed:
                # ! TODO
                pass
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

    def _initialize_driver(self) -> bool:
        """Initializes the Selenium WebDriver if not already done. If initialization fails, it returns False."""
        if not self.driver:
            self.driver = setup_driver()
        try:
            self.driver.get(self.product_url)
            time.sleep(3)  # Let JavaScript render
            self.html_body = self.driver.page_source
            return True
        except WebDriverException as e:
            logger.error(f"WebDriverException: {e}")
            self.driver.quit()
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.driver.quit()
        return False
    
    def _initialize_requests(self) -> bool:
        """Initializes the requests response if not already done. If initialization fails, it returns False."""
        try:
            response = requests.get(self.product_url)
            response.raise_for_status()
            self.requests_response = response
            self.html_body = response.text
            return True
        except requests.RequestException as e:
            logger.error(f"RequestException: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return False
    
    def _initialize_soup(self) -> bool:
        """Initializes the BeautifulSoup object if not already done. If initialization fails, it returns False."""
        try:
            if not self.soup:
                self.soup = BeautifulSoup(self.html_body, "html.parser")
            return True
        except requests.RequestException as e:
            logger.error(f"RequestException: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return False
    
    def _call_driver_insteadof_requests(self):
        """If requests could not call website well use driver instead
        """
        pass
    
    def _close_driver(self) -> None:
        """Close selenium driver if exists"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
    
    # ! Following methods used to scrape data from web page
    
    def _scrape_json_ld(self) -> dict|None:
        """Extract product data from JSON-LD script tags

        Returns:
            dict|None: Returns dict if data found in the 'ld+script' script tag. If no data found or error happened returns None.
        """
        try:
            json_ld_data = {}
            if self.soup:
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
    
    def _get_generic_field_value(self, field_name: str, default_return_value: Any, css_selector: str='', multi_value: bool=False) -> str:
        """Extracts the value of the field_name of the product from the BeautifulSoup object or Selenium driver."""
        try:
            logger.info(f'try to extract data for "{field_name}" field...')
            field_data: dict = self._find_product_field_data(field_name=field_name,css_selector=css_selector)
            # print(f'FIELD DATA: {field_data}')
            field_value_list = field_data.get(field_name, default_return_value)
        except Exception as e:
            logger.error(f"Error extracting {field_name}: {e}")
        if multi_value:
            return field_value_list if field_value_list else default_return_value
        return field_value_list[0] if field_value_list else default_return_value
    
    def _find_product_field_data(self, field_name: str, css_selector: str='') -> dict:
        """Scrape product data.
        field_name: The name of the field to extract (e.g., title, price, description).
        css_selctor: The CSS selector to use for scraping"""
        try:
            data: dict = {f'{field_name}': [], 'status': '', 'msg': ''}
            if not css_selector:
                raise ValueError("css_selector must be provided")
            if not self.soup:
                raise ValueError("BeautifulSoup must be provided")
            tags = self.soup.select(f"{css_selector}")
            for tag in tags:
                if tag.get_text(strip=True):
                    data[f'{field_name}'].append(tag.get_text(strip=True))
            data.update({'status': 'ok', 'msg': f'Successfully extracted "{field_name}"'})
        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
            data.update({'status': 'nok', 'msg': f'Error: {ve}'})
        except Exception as e:
            logger.error(f"Error extracting {field_name}: {e}")
            data.update({'status': 'nok', 'msg': f'Error: cannot extract {field_name}'})
        return data
    # ! following methods used to scrape data for a single field
    def _find_name_title(self):
        """Get product name value manually
        """
        try:
            pass
        except Exception as e:
            logger.error(f'Error in getting product name value: {e.__str__()}')
        return ''
