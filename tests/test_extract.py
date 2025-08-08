import unittest
from unittest.mock import patch, MagicMock
from application.extractor.extract import Extractor

class TestExtractor(unittest.TestCase):
    def setUp(self):
        patcher_config = patch("application.extractor.extract.config")
        self.mock_config = patcher_config.start()
        self.mock_config.METHOD = "requests"
        self.addCleanup(patcher_config.stop)

        patcher_logger = patch("application.extractor.extract.logger")
        self.mock_logger = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

    def test_extractor_init_defaults(self):
        url = "http://example.com/product"
        extractor = Extractor(url)
        self.assertEqual(extractor.product_url, url)
        self.assertEqual(extractor.product_title, 'N/A')
        self.assertEqual(extractor.product_price, 0.0)
        self.assertEqual(extractor.product_description, 'N/A')
        self.assertEqual(extractor.product_images, [])
        self.assertEqual(extractor.product_name, 'N/A')
        self.assertEqual(extractor.company_name, 'N/A')
        self.assertEqual(extractor.categories, [])
        self.assertIsNone(extractor.driver)
        self.assertIsNone(extractor.soup)

    @patch("application.extractor.extract.BeautifulSoup")
    @patch("application.extractor.extract.requests.get")
    def test_initialize_soup_success(self, mock_get, mock_bs):
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        extractor = Extractor("http://example.com/product")
        self.assertTrue(extractor._initialize_soup())
        mock_get.assert_called_once()
        mock_bs.assert_called_once()

    @patch("application.extractor.extract.requests.get")
    def test_initialize_soup_failure(self, mock_get):
        mock_get.side_effect = Exception("Request failed")
        extractor = Extractor("http://example.com/product")
        self.assertFalse(extractor._initialize_soup())

    @patch("application.extractor.extract.setup_driver")
    def test_initialize_driver_success(self, mock_setup_driver):
        mock_driver = MagicMock()
        mock_setup_driver.return_value = mock_driver
        extractor = Extractor("http://example.com/product", method="selenium")
        extractor.driver = None
        self.assertTrue(extractor._initialize_driver())
        mock_driver.get.assert_called_once()

    @patch("application.extractor.extract.setup_driver")
    def test_initialize_driver_failure(self, mock_setup_driver):
        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("WebDriverException")
        mock_setup_driver.return_value = mock_driver
        extractor = Extractor("http://example.com/product", method="selenium")
        extractor.driver = None
        self.assertFalse(extractor._initialize_driver())

    def test_check_method_valid(self):
        extractor = Extractor("http://example.com/product")
        extractor.soup = MagicMock()
        self.assertEqual(extractor._check_method("requests"), "requests")
        extractor.driver = MagicMock()
        self.assertEqual(extractor._check_method("selenium"), "selenium")

    def test_check_method_invalid(self):
        extractor = Extractor("http://example.com/product")
        self.assertIsNone(extractor._check_method("invalid"))

    def test_find_product_field_data_requests(self):
        soup = MagicMock()
        soup.select.return_value = [MagicMock(get_text=MagicMock(return_value="Test Product"))]
        extractor = Extractor("http://example.com/product")
        extractor.soup = soup
        data = extractor._find_product_field_data("title", css_selector=".product_title", method="requests")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["title"], ["Test Product"])

    def test_find_product_field_data_selenium(self):
        driver = MagicMock()
        elem = MagicMock()
        elem.text = "Test Product"
        driver.find_elements.return_value = [elem]
        extractor = Extractor("http://example.com/product", method="selenium")
        extractor.driver = driver
        data = extractor._find_product_field_data("title", css_selector=".product_title", method="selenium")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["title"], ["Test Product"])

    def test_get_generic_field_value_single(self):
        extractor = Extractor("http://example.com/product")
        extractor._find_product_field_data = MagicMock(return_value={"title": ["Test Product"]})
        value = extractor._get_generic_field_value("title", "N/A", css_selector=".product_title")
        self.assertEqual(value, "Test Product")

    def test_get_generic_field_value_multi(self):
        extractor = Extractor("http://example.com/product")
        extractor._find_product_field_data = MagicMock(return_value={"images": ["img1.jpg", "img2.jpg"]})
        value = extractor._get_generic_field_value("images", [], css_selector=".img", multi_value=True)
        self.assertEqual(value, ["img1.jpg", "img2.jpg"])

    def test_extract_requests(self):
        extractor = Extractor("http://example.com/product")
        extractor._initialize_soup = MagicMock(return_value=True)
        extractor._get_generic_field_value = MagicMock(side_effect=[
            "Test Title", 9.99, "Test Desc", ["img1.jpg"], "Test Company", ["cat1"]
        ])
        extractor.soup = MagicMock()
        extractor.driver = None
        self.mock_config.METHOD = "requests"
        data = extractor.extract()
        self.assertEqual(data["name"], "Test Title")
        self.assertEqual(data["price"], 9.99)
        self.assertEqual(data["description"], "Test Desc")
        self.assertEqual(data["images"], ["img1.jpg"])
        self.assertEqual(data["company_name"], "Test Company")
        self.assertEqual(data["category"], ["cat1"])

    def test_extract_selenium(self):
        extractor = Extractor("http://example.com/product", method="selenium")
        extractor._initialize_driver = MagicMock(return_value=True)
        extractor._get_generic_field_value = MagicMock(side_effect=[
            "Test Title", 9.99, "Test Desc", ["img1.jpg"], "Test Company", ["cat1"]
        ])
        extractor.driver = MagicMock()
        extractor.soup = None
        self.mock_config.METHOD = "selenium"
        data = extractor.extract()
        self.assertEqual(data["name"], "Test Title")
        self.assertEqual(data["price"], 9.99)
        self.assertEqual(data["description"], "Test Desc")
        self.assertEqual(data["images"], ["img1.jpg"])
        self.assertEqual(data["company_name"], "Test Company")
        self.assertEqual(data["category"], ["cat1"])