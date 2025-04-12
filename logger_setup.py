"""
This module sets up advanced logging with a consistent format.
# It is designed to be imported and used in other modules of the application.
# It uses the logging library to create a logger that can be reused across different modules.
# The logger is configured to output messages to the console with a specific format.
"""


import logging
import sys

def setup_logger(name):
    """Set up and return a logger with the specified name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Console handler for outputting logs to stdout
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    
    # Formatter for log messages
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    ch.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(ch)
    
    return logger
