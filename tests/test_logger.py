from logger_setup import setup_logger
import logging
import unittest


class TestLoggerSetup(unittest.TestCase):
    """Test class for logger setup."""
    
    def setUp(self):
        pass

    def test_logger_setup(self):
        """Test the logger setup."""
        logger = setup_logger("test_logger")
        assert logger is not None, "Logger should be set up successfully."
        assert isinstance(logger, logging.Logger), "Logger should be an instance of logging.Logger."
        logger.info("test_logger_setup test passed.")

    
    def tearDown(self):
        print("\nCleaning up after tests 'test_logger'...\n")
