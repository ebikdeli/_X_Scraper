import unittest
from unittest.mock import patch, MagicMock
from application.extractor.robots_parser import RobotsTxtParser

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
        mock_get.side_effect = Exception("Connection error")

        parser = RobotsTxtParser("https://example.com")
        # Should not raise, just print error
        parser._scrape_requests()
        self.assertEqual(parser.user_agents, {})
        self.assertEqual(parser.sitemaps, [])
