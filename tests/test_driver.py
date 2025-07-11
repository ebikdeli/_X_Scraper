import unittest
from unittest.mock import patch, MagicMock
from application.driver.chrome import setup_driver


class TestSetupDriver(unittest.TestCase):
    @patch("application.driver.chrome.webdriver.Chrome")
    @patch("application.driver.chrome.Options")
    def test_setup_driver_default(self, mock_options, mock_chrome):
        """Test setup_driver returns a Chrome driver instance with default settings."""
        mock_options_instance = MagicMock()
        mock_options.return_value = mock_options_instance
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        driver = setup_driver()
        mock_options.assert_called_once()
        mock_chrome.assert_called_once_with(options=mock_options_instance)
        self.assertEqual(driver, mock_driver)

    @patch("application.driver.chrome.webdriver.Chrome")
    @patch("application.driver.chrome.Options")
    def test_setup_driver_headless(self, mock_options, mock_chrome):
        """Test setup_driver returns a Chrome driver instance in headless mode."""
        mock_options_instance = MagicMock()
        mock_options.return_value = mock_options_instance
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        driver = setup_driver(headless=True)
        mock_options_instance.add_argument.assert_any_call("--headless")
        mock_chrome.assert_called_once_with(options=mock_options_instance)
        self.assertEqual(driver, mock_driver)

    @patch("application.driver.chrome.random.choice")
    @patch("application.driver.chrome.PROXIES", new=["http://proxy1:8080", "http://proxy2:8080"])
    @patch("application.driver.chrome.webdriver.Chrome")
    @patch("application.driver.chrome.Options")
    def test_setup_driver_with_proxy(self, mock_options, mock_chrome, mock_random_choice):
        """Test setup_driver returns a Chrome driver instance with proxy rotation."""
        mock_options_instance = MagicMock()
        mock_options.return_value = mock_options_instance
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        mock_random_choice.return_value = "http://proxy1:8080"

        driver = setup_driver(use_proxy=True)
        mock_options_instance.add_argument.assert_any_call('--proxy-server=http://proxy1:8080')
        mock_chrome.assert_called_once_with(options=mock_options_instance)
        self.assertEqual(driver, mock_driver)
