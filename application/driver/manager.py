import atexit
from typing import Optional

from selenium.webdriver.chrome.webdriver import WebDriver

from application.driver.chrome import setup_driver, shutdown_driver


class DriverManager:
    """Manage a single Selenium Chrome driver for the app lifetime."""

    _driver: Optional[WebDriver] = None

    @classmethod
    def get_driver(cls) -> WebDriver:
        if cls._driver is None:
            cls._driver = setup_driver()
        return cls._driver

    @classmethod
    def shutdown(cls) -> None:
        shutdown_driver()
        cls._driver = None


atexit.register(DriverManager.shutdown)
