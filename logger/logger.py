import logging
import os

def setup_logger(log_file="scraper.log"):
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logging.basicConfig(
        filename=os.path.join("logs", log_file),
        # level=logging.DEBUG,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)
