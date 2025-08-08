from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from typing import Optional, Any
from application.driver.chrome import setup_driver
import requests
import config
from bs4 import BeautifulSoup, Tag
import time
from logger.logger import setup_logger


logger = setup_logger('__name__')


class Extractor:
    """A class to extract product data from e-commerce websites."""
    def __init__(self, product_url: str, method: str=config.METHOD, driver: WebDriver|None=None, soup: BeautifulSoup|None=None):
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
            # Extract product data using Selenium
            self.product_data = {
                "url": self.product_url,
                "name": self._get_generic_field_value('title', '', css_selector='.product_title'),
                "price": self._get_generic_field_value('price', 0, css_selector='.woocommerce-Price-amount'),
                "description": self._get_generic_field_value('description', '', css_selector='.woocommerce-product-details__short-description'),
                "images": self._get_generic_field_value('images', [], css_selector='.woocommerce-product-gallery__image img', multi_value=True),
                "company_name": self._get_generic_field_value('company_name', 'Unknown', css_selector='.brand, .manufacturer'),
                "category": self._get_generic_field_value('category', 'Uncategorized', css_selector='.posted_in a'),
            }
        except Exception:
            if self.driver:
                self.driver.quit()
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
            return False
    
    def _initialize_soup(self) -> bool:
        """Initializes the BeautifulSoup object if not already done. If initialization fails, it returns False."""
        try:
            response = requests.get(self.product_url, timeout=10)
            response.raise_for_status()
            if not self.soup:
                self.soup = BeautifulSoup(response.text, "html.parser")
            return True
        except requests.RequestException as e:
            logger.error(f"RequestException: {e}")
            return False
    
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
                for elem in elements:
                    if elem.text.strip():
                        data[f'{field_name}'].append(elem.text.strip())
            # Extract data based on soup
            if chosen_method == "requests" and self.soup:
                if not css_selector:
                    raise ValueError("css_selector must be provided for Requests method.")
                tags = self.soup.select(f"{css_selector}")
                for tag in tags:
                    if tag.get_text(strip=True):
                        data[f'{field_name}'].append(tag.get_text(strip=True))
            else:
                raise ValueError("Invalid method specified or neither soup nor driver is available.")
            data.update({'status': 'ok', 'msg': f'Successfully extracted "{field_name}" field data using "{chosen_method}"'})
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
            if method:
                chosen_method = self._check_method(method)
                if not chosen_method:
                    raise ValueError("Invalid method specified or neither soup nor driver is available.")
            field_data: dict = self._find_product_field_data(field_name=field_name,css_selector=css_selector, xpath=xpath, method=method)
            field_value_list = field_data.get(field_name, default_return_value)
        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
        except Exception as e:
            logger.error(f"Error extracting {field_name}: {e}")
        if multi_value:
            return field_value_list if field_value_list else default_return_value
        return field_value_list[0] if field_value_list else default_return_value
    