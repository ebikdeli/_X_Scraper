import logging
import os
import sys

def setup_logger(log_file="scraper.log", logger_name=None):
    """
    Set up logger with both file and console handlers
    
    Args:
        log_file: Name of the log file (default: "scraper.log")
        logger_name: Name for the logger, use __name__ from calling module
        If None, creates a generic logger
    """
    # Create logs directory
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Use provided name or create generic one
    if logger_name is None:
        logger_name = "app"
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Check if handlers already exist to avoid duplicates
    if logger.handlers:
        return logger
    
    # Formatter for consistent log messages
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # File Handler - saves ALL levels (DEBUG and above)
    file_path = os.path.join(log_dir, log_file)
    file_handler = logging.FileHandler(file_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Save everything
    file_handler.setFormatter(formatter)
    
    # Console Handler - only important messages
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Only INFO and above to console
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger (avoid duplicate messages)
    logger.propagate = False
    
    return logger