import unittest
from unittest.mock import patch, MagicMock
from application.extractor.robots_parser import RobotsTxtParser, RobotsExtLinks
from requests.exceptions import RequestException

class TestRobotsTxtParserRequests(unittest.TestCase):
    
    @patch("application.extractor.robots_parser.requests.get")
    def test_scrape_requests_success(self, mock_get):
        # Mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
            User-agent: *
            Disallow: /private/
            Allow: /public/
            Sitemap: https://example.com/sitemap.xml
        """
        mock_get.return_value = mock_response

        parser = RobotsTxtParser("https://example.com")
        parser._scrape_requests()

        self.assertIn("*", parser.user_agents)
        self.assertIn("/private/", parser.user_agents["*"]["disallow"])
        self.assertIn("/public/", parser.user_agents["*"]["allow"])
        self.assertIn("https://example.com/sitemap.xml", parser.sitemaps)

    @patch("application.extractor.robots_parser.requests.get")
    def test_scrape_requests_failure(self, mock_get):
        # Simulate a requests exception
        mock_get.side_effect = RequestException("Connection error")

        parser = RobotsTxtParser("https://example.com")
        parser._scrape_requests()
        self.assertEqual(parser.user_agents, {})
        self.assertEqual(parser.sitemaps, [])

    def test_parse_content_multiple_user_agents(self):
        parser = RobotsTxtParser("https://example.com")
        content = """
        User-agent: Googlebot
        Disallow: /nogoogle/
        User-agent: Bingbot
        Disallow: /nobing/
        Allow: /public/
        """
        parser._parse_content(content)
        self.assertIn("Googlebot", parser.user_agents)
        self.assertIn("Bingbot", parser.user_agents)
        self.assertIn("/nogoogle/", parser.user_agents["Googlebot"]["disallow"])
        self.assertIn("/nobing/", parser.user_agents["Bingbot"]["disallow"])
        self.assertIn("/public/", parser.user_agents["Bingbot"]["allow"])

    def test_is_allowed(self):
        parser = RobotsTxtParser("https://example.com")
        parser.user_agents = {
            "*": {"allow": ["/public/"], "disallow": ["/private/", "/tmp/"]},
            "TestBot": {"allow": ["/special/"], "disallow": ["/secret"]}
        }
        self.assertFalse(parser.is_allowed("*", "/private/data"))
        self.assertTrue(parser.is_allowed("*", "/public/info"))
        self.assertFalse(parser.is_allowed("TestBot", "/secret/"))
        self.assertTrue(parser.is_allowed("TestBot", "/special/page"))
        self.assertTrue(parser.is_allowed("UnknownBot", "/anywhere"))

    def test_get_sitemaps_and_rules(self):
        parser = RobotsTxtParser("https://example.com")
        parser.sitemaps = ["https://example.com/sitemap.xml"]
        parser.user_agents = {"*": {"allow": ["/"], "disallow": []}}
        self.assertEqual(parser.get_sitemaps(), ["https://example.com/sitemap.xml"])
        self.assertEqual(parser.get_rules("*"), {"allow": ["/"], "disallow": []})
        self.assertIsNone(parser.get_rules("NoBot"))

    @patch("application.extractor.robots_parser.setup_driver")
    def test_scrape_selenium_success(self, mock_setup_driver):
        mock_driver = MagicMock()
        mock_driver.page_source = """
            User-agent: *
            Disallow: /private/
            Allow: /public/
        """
        mock_setup_driver.return_value = mock_driver
        parser = RobotsTxtParser("https://example.com")
        parser.driver = None
        parser._scrape_selenium()
        self.assertIn("*", parser.user_agents)
        self.assertIn("/private/", parser.user_agents["*"]["disallow"])
        self.assertIn("/public/", parser.user_agents["*"]["allow"])

class TestRobotsExtLinks(unittest.TestCase):
    def setUp(self):
        self.mock_parser = MagicMock()
        self.mock_parser.get_sitemaps.return_value = [
            "https://example.com/sitemap.xml",
            "https://example.com/products.xml"
        ]
        self.ext_links = RobotsExtLinks(self.mock_parser)

    def test_check_sm_product_link(self):
        self.assertTrue(self.ext_links._is_url_product("https://example.com/product-123.xml"))
        self.assertFalse(self.ext_links._is_url_product("https://example.com/category.xml"))

    def test_check_sm_link(self):
        self.assertTrue(self.ext_links._is_url_sitemap("https://example.com/sitemap.xml"))
        self.assertTrue(self.ext_links._is_url_sitemap("https://example.com/other.xml"))
        self.assertFalse(self.ext_links._is_url_sitemap("https://example.com/page.html"))

    @patch("application.extractor.robots_parser.requests.get")
    def test_fetch_content_requests(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<xml>data</xml>"
        mock_get.return_value = mock_response
        self.ext_links.driver = None
        with patch("application.extractor.robots_parser.config", create=True) as mock_config:
            mock_config.METHOD = "requests"
            content = self.ext_links._fetch_content("https://example.com/sitemap.xml")
            self.assertEqual(content, "<xml>data</xml>")

    @patch("application.extractor.robots_parser.setup_driver")
    def test_fetch_content_selenium(self, mock_setup_driver):
        mock_driver = MagicMock()
        mock_driver.page_source = "<xml>selenium</xml>"
        mock_setup_driver.return_value = mock_driver
        with patch("application.extractor.robots_parser.config", create=True) as mock_config:
            mock_config.METHOD = "selenium"
            self.ext_links.driver = None
            content = self.ext_links._fetch_content("https://example.com/sitemap.xml")
            self.assertEqual(content, "<xml>selenium</xml>")

    def test_extract_links(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/product1</loc></url>
            <url><loc>https://example.com/product2</loc></url>
        </urlset>
        """
        links = self.ext_links._extract_links(xml)
        self.assertEqual(len(links), 2)
        self.assertIn("https://example.com/product1", links)
        self.assertIn("https://example.com/product2", links)

    @patch.object(RobotsExtLinks, "_fetch_content")
    def test_find_product_sitemap_links(self, mock_fetch_content):
        # Simulate a sitemap with two product links and one nested sitemap
        sitemap_xml = """
        <urlset>
            <url><loc>https://example.com/product1</loc></url>
            <url><loc>https://example.com/product2</loc></url>
        </urlset>
        """
        nested_sitemap_xml = """
        <sitemapindex>
            <sitemap><loc>https://example.com/products.xml</loc></sitemap>
        </sitemapindex>
        """
        def side_effect(url):
            if url.endswith("sitemap.xml"):
                return nested_sitemap_xml
            elif url.endswith("products.xml"):
                return sitemap_xml
            return ""
        mock_fetch_content.side_effect = side_effect

        ext_links = RobotsExtLinks(self.mock_parser)
        ext_links._is_url_product = lambda url: "product" in url
        ext_links._is_url_sitemap = lambda url: "sitemap" in url or "products" in url
        links = ext_links.find_product_sitemap_links()
        self.assertIn("https://example.com/products.xml", links)

    def test_close_driver(self):
        ext_links = RobotsExtLinks(self.mock_parser)
        mock_driver = MagicMock()
        ext_links.driver = mock_driver
        ext_links.close()
        mock_driver.quit.assert_called_once()
        self.assertIsNone(ext_links.driver)
