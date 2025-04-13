"""
This is the main entry point that uses multiprocessing to consume messages from the RabbitMQ queue and process them.
"""


import json
from multiprocessing import Pool, cpu_count
from mq_handler import send_message, start_consuming
from scraper import scrape_amazon_product
from mongodb_handler import save_to_mongodb
from logger_setup import setup_logger
from config import AMAZON_URLS, QUEUE_NAME

try:

    input('WQANNT QUIET?')
    exit()
except Exception as e:
    print(e.__str__())
    input('ERROR///')
    exit()

logger = setup_logger("main")

def process_message(ch, method, properties, body):
    """Callback function for RabbitMQ message consumption."""
    url_data = json.loads(body)
    url = url_data.get("url")
    if url:
        product = scrape_amazon_product(url)
        if product:
            save_to_mongodb(product, logger)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def worker():
    """Worker to start consuming messages from RabbitMQ."""
    start_consuming(QUEUE_NAME, process_message)

def main():
    # Optionally: Send URLs to the queue for processing.
    for url in AMAZON_URLS:
        send_message(QUEUE_NAME, {"url": url})
    
    # Determine the number of worker processes
    num_workers = min(len(AMAZON_URLS), cpu_count())
    logger.info(f"Starting message queue consumers with {num_workers} processes...")
    
    # Create a pool of processes to handle messages concurrently.
    with Pool(processes=num_workers) as pool:
        # Each pool worker will run the worker() function.
        pool.map(lambda _: worker(), range(num_workers))

if __name__ == "__main__":
    main()
