import unittest
from core.driver_setup import setup_driver


class TestSetupDriver(unittest.TestCase):
    def setUp(self):
        return super().setUp()
    
    def test_setup_driver(self):
        """Test setup driver"""
        url = 'https://en.wikipedia.org/wiki/Google'
        driver = setup_driver(headless=False)
        driver.get(url)
        print('Driver is setup successfully')
        driver.close()
        
    def test_headless_setup_driver(self):
        """Test setup driver in headless mode"""
        url = 'https://en.wikipedia.org/wiki/Google'
        driver = setup_driver()
        driver.get(url)
        print('Driver is setup successfully')
        driver.close()
        
    def test_proxy_setup_driver(self):
        """Test setup driver using proxies"""
        pass
