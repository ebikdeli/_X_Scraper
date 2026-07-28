import unittest
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException
from selenium.common.exceptions import WebDriverException
from application.extractor.extract import Extractor


class TestExtractor(unittest.TestCase):
    def setUp(self):
        patcher_config = patch("application.extractor.extract.config")
        self.mock_config = patcher_config.start()
        self.mock_config.METHOD = "requests"
        self.mock_config.REUSE_DRIVER = False
        self.mock_config.SLEEP_TIME = 0
        self.mock_config.REQUEST_TIMEOUT = 5
        self.addCleanup(patcher_config.stop)

        patcher_logger = patch("application.extractor.extract.logger")
        self.mock_logger = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

    def test_extractor_init_defaults(self):
        extractor = Extractor("http://example.com/product")
        self.assertEqual(extractor.product_url, "http://example.com/product")
        self.assertEqual(extractor.product_data.title, '')
        self.assertEqual(extractor.product_data.price, 0)
        self.assertEqual(extractor.product_data.description, '')
        self.assertEqual(extractor.product_data.images, [])
        self.assertIsNone(extractor.driver)
        self.assertIsNone(extractor.soup)

    @patch("application.extractor.extract.requests.get")
    def test_initialize_requests_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        extractor = Extractor("http://example.com/product")
        self.assertTrue(extractor._initialize_requests())
        self.assertIsNotNone(extractor.soup)

    @patch("application.extractor.extract.requests.get")
    def test_initialize_requests_failure(self, mock_get):
        mock_get.side_effect = RequestException("fail")
        extractor = Extractor("http://example.com/product")
        self.assertFalse(extractor._initialize_requests())

    @patch("application.extractor.extract.setup_driver")
    def test_initialize_driver_success(self, mock_setup_driver):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body><h1>Test</h1></body></html>"
        mock_setup_driver.return_value = mock_driver

        extractor = Extractor("http://example.com/product", method="selenium")
        self.assertTrue(extractor._Extractor__initialize_driver())
        mock_driver.get.assert_called_once()
        self.assertIsNotNone(extractor.soup)

    @patch("application.extractor.extract.setup_driver")
    def test_initialize_driver_failure(self, mock_setup_driver):
        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("load failed")
        mock_setup_driver.return_value = mock_driver

        extractor = Extractor("http://example.com/product", method="selenium")
        self.assertFalse(extractor._Extractor__initialize_driver())

    @patch("application.extractor.extract.restart_driver")
    @patch("application.extractor.extract.setup_driver")
    def test_initialize_driver_restarts_after_webdriver_failure(self, mock_setup_driver, mock_restart_driver):
        dead_driver = MagicMock()
        dead_driver.get.side_effect = WebDriverException("session stopped")
        fresh_driver = MagicMock()
        fresh_driver.page_source = "<html><body><h1>Recovered</h1></body></html>"
        mock_setup_driver.return_value = dead_driver
        mock_restart_driver.return_value = fresh_driver

        extractor = Extractor("http://example.com/product", method="selenium")

        self.assertTrue(extractor._Extractor__initialize_driver())
        mock_restart_driver.assert_called_once()
        fresh_driver.get.assert_called_once_with("http://example.com/product")
        self.assertIsNotNone(extractor.soup)

    def test_scrape_json_ld_script_tags(self):
        extractor = Extractor("http://example.com/product")
        extractor.html_body = '<script type="application/ld+json">{"@type":"Product","name":"Test Product"}</script>'
        extractor._initialize_soup()
        json_ld_data = extractor._scrape_json_ld_script_tags()
        self.assertIsInstance(json_ld_data, dict)
        self.assertEqual(json_ld_data.get('@type'), 'Product')

    def test_missing_soup_returns_empty_values(self):
        extractor = Extractor("http://example.com/product")
        extractor.soup = None

        self.assertEqual(extractor._find_title(), '')
        self.assertEqual(extractor._find_price(), 0)
        self.assertEqual(extractor._find_description(), '')
        self.assertEqual(extractor._find_images(), [])
        self.assertEqual(extractor._find_company_name(), '')
        self.assertEqual(extractor._find_category(), [])
        self.assertEqual(extractor._scrape_meta(), {})

    @patch("application.extractor.extract.upsert_product_data", return_value=True)
    @patch("application.extractor.extract.requests.get")
    def test_scrape_with_json_ld(self, mock_get, mock_upsert):
        mock_response = MagicMock()
        mock_response.text = '<html><head><script type="application/ld+json">{"@type":"Product","name":"Test Product","offers":{"price":"100"}}</script></head><body></body></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        extractor = Extractor("http://example.com/product")
        result = extractor.scrape()
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['data']['title'], 'Test Product')
        self.assertEqual(result['data']['price'], 100)
