"""
Configuration file for the _X_Scraper project.
This file holds configuration parameters such as proxy lists, target URLs, and RabbitMQ settings for message queuing.
"""

# List of proxies to rotate through. Replace with your actual proxies.
PROXIES: list[str] = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080"
]

# Sample Amazon URLs to scrape. Replace these with real product URLs.
AMAZON_URLS: list[str] = [
    "https://www.amazon.com/dp/B08N5WRWNW",
    "https://www.amazon.com/dp/B07XJ8C8F5",
    "https://www.amazon.com/dp/B09G3HRMVB"
]

# RabbitMQ settings
RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
QUEUE_NAME: str = "amazon_scrape_queue"

# Default ethod to used (requests or selenium)
METHOD: str = 'selenium'

# While using selenium, Reuse current driver for the next webpage.
REUSE_DRIVER: bool = True

# Sleeping time in selenium
SLEEP_TIME: int = 4

# Selenium driver configurations
SELENIUM_HEADLESS: bool = False
SELENIUM_USE_PROXY: bool = False
SELENIUM_OPTIMIZED: bool = True
SELENIUM_SILENT_MODE_LEVEL: int = 2
SELENIUM_WINDOWZ_SIZE: str = '800,600'  # width,height
SELENIUM_DISABLE_CSS: bool = False
SELENIUM_DISABLE_IMAGE: bool = True
SELENIUM_IMPLICIT_WAIT: int = 120
SELENIUM_TIMEOUT: int = 50
