"""
Configuration file for the _X_Scraper project.
This file holds configuration parameters such as proxy lists, target URLs, and RabbitMQ settings for message queuing.
"""

# List of proxies to rotate through. Replace with your actual proxies.
PROXIES = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080"
]

# Sample Amazon URLs to scrape. Replace these with real product URLs.
AMAZON_URLS = [
    "https://www.amazon.com/dp/B08N5WRWNW",
    "https://www.amazon.com/dp/B07XJ8C8F5",
    "https://www.amazon.com/dp/B09G3HRMVB"
]

# RabbitMQ settings
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
QUEUE_NAME = "amazon_scrape_queue"
