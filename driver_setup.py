"""
This module sets up the Selenium Chrome driver with optimized options, including rotating proxies.
It is designed to be imported and used in the scraping logic.
It uses the selenium library to create a headless Chrome driver instance with specific configurations.
"""


import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from config import PROXIES

def setup_driver():
    """Initialize and return a headless Selenium Chrome driver with proxy rotation."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")          # Run in headless mode for efficiency
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    # Rotate proxy
    if PROXIES:
        proxy = random.choice(PROXIES)
        chrome_options.add_argument(f'--proxy-server={proxy}')
    
    # Create the Chrome driver instance
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver
