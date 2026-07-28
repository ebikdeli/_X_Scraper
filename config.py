"""
Configuration for the X_Scraper project.
Values can be overridden with environment variables prefixed by X_SCRAPER_.
"""

import os
from typing import List


def _env_list(name: str, default: List[str]) -> List[str]:
    """Get a list of strings from an environment variable, splitting by commas.
    If the environment variable is not set, return the default list.
    """
    value: str|None = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(',') if item.strip()]

# Configuration variables with default values, can be overridden by environment variables

PROXIES: List[str] = _env_list(
    'X_SCRAPER_PROXIES',
    [
        'http://proxy1.example.com:8080',
        'http://proxy2.example.com:8080',
        'http://proxy3.example.com:8080',
    ]
)

METHOD: str = os.getenv('X_SCRAPER_METHOD', 'selenium')
DB_FILE: str = os.getenv('X_SCRAPER_DB_FILE', 'scraped_data.db')
REQUEST_TIMEOUT: int = int(os.getenv('X_SCRAPER_REQUEST_TIMEOUT', '10'))
SLEEP_TIME: int = int(os.getenv('X_SCRAPER_SLEEP_TIME', '4'))
SELENIUM_HEADLESS: bool = os.getenv('X_SCRAPER_SELENIUM_HEADLESS', 'False').lower() in ('1', 'true', 'yes')
SELENIUM_USE_PROXY: bool = os.getenv('X_SCRAPER_SELENIUM_USE_PROXY', 'False').lower() in ('1', 'true', 'yes')
SELENIUM_OPTIMIZED: bool = os.getenv('X_SCRAPER_SELENIUM_OPTIMIZED', 'True').lower() in ('1', 'true', 'yes')
SELENIUM_SILENT_MODE_LEVEL: int = int(os.getenv('X_SCRAPER_SELENIUM_SILENT_MODE_LEVEL', '2'))
SELENIUM_WINDOW_SIZE: str = os.getenv('X_SCRAPER_SELENIUM_WINDOW_SIZE', '800,600')
SELENIUM_DISABLE_CSS: bool = os.getenv('X_SCRAPER_SELENIUM_DISABLE_CSS', 'False').lower() in ('1', 'true', 'yes')
SELENIUM_DISABLE_IMAGE: bool = os.getenv('X_SCRAPER_SELENIUM_DISABLE_IMAGE', 'True').lower() in ('1', 'true', 'yes')
SELENIUM_IMPLICIT_WAIT: int = int(os.getenv('X_SCRAPER_SELENIUM_IMPLICIT_WAIT', '10'))
SELENIUM_TIMEOUT: int = int(os.getenv('X_SCRAPER_SELENIUM_TIMEOUT', '50'))
