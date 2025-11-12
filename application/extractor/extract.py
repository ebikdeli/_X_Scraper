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
import requests
import config
from bs4 import BeautifulSoup, Tag
import time
from logger.logger import setup_logger


logger = setup_logger('scraper.log', __name__)


class Extractor:
    """A class to extract product data from e-commerce websites.\n
    Every methods that scrape a single attribute can be called with arbitrary scraping method (For eg, we can scrape title with selenium and image using Beautiful soup. But beware because it could have additional proccessing overhead).\n"""
    def __init__(self, product_url: str, method: str=config.METHOD, driver: WebDriver|None=None, soup: BeautifulSoup|None=None):
        # Initialize product attributes with default values one by one    
        self.product_url = product_url
        self.product_title: str = 'N/A'
        self.product_price: float = 0.0
        self.product_description: str = 'N/A'
        self.product_images: list = []
        self.product_name: str = 'N/A'
        self.company_name: str = 'N/A'
        self.categories: list = []
        self.driver: Optional[WebDriver] = None
        self.soup: Optional[BeautifulSoup] = None
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
        self.driver = driver
        self.soup = soup
        self.method = method

    def extract(self) -> dict:
        """
        Extracts product data from a given e-commerce product URL.

        Args:
            url (str): The product page URL.

        Returns:
            dict: A dictionary containing product attributes such as title, price, description,
                images, name, company_name, category, and other standard product data.
        """
        try:
            if config.METHOD == "selenium":
                if not self._initialize_driver():
                    return {'status': 'error', 'msg': 'WebDriverException occurred', 'data': self.product_data}
            elif config.METHOD == "requests":
                if not self._initialize_soup():
                    return {'status': 'error', 'msg': 'RequestException occurred', 'data': self.product_data}
            logger.info(f'Product url to be extracted:\n{self.product_url}')
            # Extract product data using method
            # ! MUST WORK A LOT ON IT
            self.product_data = {
                "url": self.product_url,
                "title": self._get_generic_field_value('title', '', css_selector='.product_title'),
                "price": self._get_generic_field_value('price', 0, css_selector='.woocommerce-Price-amount'),
                "description": self._get_generic_field_value('description', '', css_selector='.woocommerce-product-details__short-description'),
                "images": self._get_generic_field_value('images', [], css_selector='.woocommerce-product-gallery__image img', multi_value=True),
                "company_name": self._get_generic_field_value('company_name', '', css_selector='.brand, .manufacturer'),
                "category": self._get_generic_field_value('category', '', css_selector='.posted_in a'),
            }
            logger.debug(f'\nAFTER EXTRACTION: data exracted for: "{self.product_url}":\n{self.product_data}')
            
            # ***
            # * Data handling could be done here. But in the Dev phase we pass this for now
            # ***
            
            # Insert-upadte product data into database
            result: bool = upsert_product_data(product_data=self.product_data)
            if not result:
                logger.warning('No product inserted into/updated from product table')
            else:
                logger.warning('Product data inserted/updated into product table')
            # Do not reuse current selenium driver
            if config.METHOD == 'selenium' and not config.REUSE_DRIVER:
                self._close_driver()
        except Exception:
            self._close_driver()
        return self.product_data

    def _initialize_driver(self) -> bool:
        """Initializes the Selenium WebDriver if not already done. If initialization fails, it returns False."""
        if not self.driver:
            self.driver = setup_driver()
        try:
            self.driver.get(self.product_url)
            time.sleep(3)  # Let JavaScript render
            return True
        except WebDriverException as e:
            logger.error(f"WebDriverException: {e}")
            self.driver.quit()
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.driver.quit()
        return False
    
    def _initialize_soup(self) -> bool:
        """Initializes the BeautifulSoup object if not already done. If initialization fails, it returns False."""
        try:
            response = requests.get(self.product_url)
            response.raise_for_status()
            if not self.soup:
                self.soup = BeautifulSoup(response.text, "html.parser")
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
    
    def _check_method(self, method: Optional[str] = None) -> str| None:
        """Checks and returns the extraction method to be used. If neither soup nor driver is available, or invalid method chosen, it logs an error."""
        if not self.soup and not self.driver:
            logger.error("Either soup or driver must be provided")
            return
        if not method and self.method:
            method = self.method
        # Determine the method to use for title extraction
        chosen_method: str = method if isinstance(method, str) and method else getattr(config, "METHOD", "requests")
        # Validate the chosen method
        if chosen_method not in ["selenium", "requests"]:
            logger.error(f"Invalid method specified: {chosen_method}. Use 'selenium' or 'requests'.")
            return
        return chosen_method

    def _find_product_field_data(self, field_name: str, css_selector: str='', xpath: str='', method: Optional[str] = None) -> dict:
        """Extracts product data based on the specified method (requests or selenium).
        field_name: The name of the field to extract (e.g., title, price, description).
        css_selctor: The CSS selector to use for extraction.(only for selenium)"""
        try:
            chosen_method = self._check_method(method)
            if not chosen_method:
                raise ValueError("Invalid method specified or neither soup nor driver is available.")
            data: dict = {f'{field_name}': [], 'status': '', 'msg': '', 'method': chosen_method}
            # Extract data based on driver
            if chosen_method == "selenium" and self.driver:
                if css_selector:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
                elif xpath:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                else:
                    raise ValueError("Either css_selctor or xpath must be provided for Selenium method.")
                # logger.debug(f"Extracting {field_name} using Selenium with css_selector: {css_selector} or xpath: {xpath}")
                for elem in elements:
                    if elem.text.strip():
                        data[f'{field_name}'].append(elem.text.strip())
            # Extract data based on soup
            elif chosen_method == "requests" and self.soup:
                if not css_selector:
                    raise ValueError("css_selector must be provided for Requests method.")
                tags = self.soup.select(f"{css_selector}")
                for tag in tags:
                    if tag.get_text(strip=True):
                        data[f'{field_name}'].append(tag.get_text(strip=True))
            else:
                raise ValueError("Invalid method specified or neither soup nor driver is available.")
            data.update({'status': 'ok', 'msg': f'Successfully extracted "{field_name}" field data using "{chosen_method}"'})
            # print(f'EXTRACTED DATA: {data}')
        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
            data.update({'status': 'nok', 'msg': f'Error: {ve}'})
        except Exception as e:
            logger.error(f"Error extracting {field_name}: {e}")
            data.update({'status': 'nok', 'msg': f'Error: cannot extract {field_name}'})
        return data
    
    def _get_generic_field_value(self, field_name: str, default_return_value: Any, css_selector: str='', xpath: str='', multi_value: bool=False, method: Optional[str] = None) -> str:
        """Extracts the value of the field_name of the product from the BeautifulSoup object or Selenium driver."""
        try:
            logger.info(f'try to extract data for "{field_name}" field...')
            if method:
                chosen_method = self._check_method(method)
                if not chosen_method:
                    raise ValueError("Invalid method specified or neither soup nor driver is available.")
            field_data: dict = self._find_product_field_data(field_name=field_name,css_selector=css_selector, xpath=xpath, method=method)
            # print(f'FIELD DATA: {field_data}')
            field_value_list = field_data.get(field_name, default_return_value)
        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
        except Exception as e:
            logger.error(f"Error extracting {field_name}: {e}")
        if multi_value:
            return field_value_list if field_value_list else default_return_value
        return field_value_list[0] if field_value_list else default_return_value
    
    def get_product_name_value(self):
        """Get product name value manually
        """
        try:
            pass
        except Exception as e:
            logger.error(f'Error in getting product name value: {e.__str__()}')
        return ''
