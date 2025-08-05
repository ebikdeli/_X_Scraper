import requests
from urllib.parse import urljoin
from typing import Dict, List, Optional, Tuple
from application.driver.chrome import setup_driver
from logger.logger import setup_logger
from selenium.webdriver.chrome.webdriver import WebDriver
import config
import re
import xml.etree.ElementTree as ET


logger = setup_logger(__name__)


class RobotsTxtParser:
    def __init__(self, base_url: str, driver: WebDriver|None=None):
        self.base_url = base_url.rstrip('/')
        self.robots_url = urljoin(self.base_url, '/robots.txt')
        self.user_agents: Dict[str, Dict[str, List[str]]] = {}
        self.sitemaps: List[str] = []
        self.driver = driver

    def _fetch_and_parse(self, method: Optional[str] = None) -> None:
        """
        Fetches and parses the robots.txt file using the specified scraping method.

        Args:
            method (str, optional): The scraping method to use ('requests' or 'selenium').
                                    If None, uses config.METHOD.
        """
        chosen_method: str = method if isinstance(method, str) and method else getattr(config, "METHOD", "requests")
        methods = {
            "requests": self._scrape_requests,
            "selenium": self._scrape_selenium,
        }
        scrape_func = methods.get(chosen_method)
        if not scrape_func:
            logger.error(f"Unknown scraping method: {chosen_method}")
            return
        try:
            scrape_func()
        except Exception as e:
            logger.error(f"Error fetching robots.txt using '{chosen_method}': {e}")
    
    def _scrape_requests(self) -> None:
        """Scrapes the robots.txt file using requests module."""
        try:
            response = requests.get(self.robots_url, timeout=5)
            response.raise_for_status()
            self._parse_content(response.text)
        except requests.RequestException as e:
            logger.error(f"Error fetching robots.txt: {e}")

    def _scrape_selenium(self) -> None:
        """Scrapes the robots.txt file using Selenium module."""
        try:
            if not self.driver:
                self.driver = setup_driver()
            self.driver.get(self.robots_url)
            content = self.driver.page_source
            if not content:
                raise ValueError("No content found in robots.txt")
            self._parse_content(content)
        except Exception as e:
            logger.error(f"Error fetching robots.txt with Selenium: {e}")

    def _parse_content(self, content: str) -> None:
        """Parses the robots.txt content."""
        current_user_agents = []
        for line in content.splitlines():
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Handle User-agent, Disallow, Allow, Sitemap
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            directive, value = parts[0].strip().lower(), parts[1].strip()
            if directive == 'user-agent':
                current_user_agents = [ua.strip() for ua in value.split(',')]
                for ua in current_user_agents:
                    if ua not in self.user_agents:
                        self.user_agents[ua] = {'allow': [], 'disallow': []}
            elif directive in ('allow', 'disallow'):
                if not current_user_agents:
                    continue  # Skip if no User-agent defined
                for ua in current_user_agents:
                    self.user_agents[ua][directive].append(value)
            elif directive == 'sitemap':
                self.sitemaps.append(value)

    def is_allowed(self, user_agent: str, path: str) -> bool:
        """Checks if a user-agent is allowed to crawl a path."""
        path = path.lstrip('/')
        for ua in [user_agent, '*']:  # Check specific UA and wildcard
            if ua in self.user_agents:
                rules = self.user_agents[ua]
                # Check disallowed paths (most specific match first)
                for disallowed in sorted(rules['disallow'], key=len, reverse=True):
                    disallowed = disallowed.lstrip('/')
                    if disallowed and path.startswith(disallowed):
                        # Check if there's an explicit Allow overriding Disallow 
                        for allowed in rules['allow']:
                            allowed = allowed.lstrip('/')
                            if allowed and path.startswith(allowed):
                                return True
                        return False
        return True  # Default: allowed if no rule blocks

    def get_sitemaps(self) -> List[str]:
        """Returns all sitemap URLs."""
        return self.sitemaps

    def get_rules(self, user_agent: str = '*') -> Optional[Dict[str, List[str]]]:
        """Returns rules for a specific user-agent."""
        return self.user_agents.get(user_agent)
    
    # USE CASE OF 'is_allowed' METHOD:
    # parser = RobotsTxtParser("https://example.com")
    # parser._fetch_and_parse()
    # if parser.is_allowed("MyBot", "/some/path"):
    #     # Proceed to crawl

class RobotsExtLinks:
    def __init__(self, robots_parser: RobotsTxtParser, driver: WebDriver|None=None) -> None:
        self.robots_parser = robots_parser
        self.product_links: List[str] = []
        self.driver = driver

    def find_product_sitemap_links(self) -> List[str]:
        """
        Read all the sitemap links extracted from robots.
        If a link belongs to a product, add it to product_links.
        Continue until no sitemap links remain to check.
        Returns:
            List[str]: All product links found in the sitemaps.
        """
        to_check: List[str] = self.robots_parser.get_sitemaps()
        checked: set[str] = set()
        if not to_check:
            logger.warning("No sitemaps found in robots.txt.")
            return self.product_links
        logger.info(f"Starting with {len(to_check)} sitemap links to check.")
        # Loop through the sitemap links to check for product links or more sitemaps
        while to_check:
            url = to_check.pop(0)
            if url in checked:
                continue
            checked.add(url)
            logger.info(f"Checking sitemap link: {url}")
            # Check if the current link is a product link or another sitemap link
            if self._is_url_product(url):
                self.product_links.append(url)
                logger.info(f"Found product link: {url}")
            elif self._is_url_sitemap(url):
                content = self._fetch_content(url)
                if content:
                    # If the link is a sitemap, find all links in it
                    logger.info(f"Found sitemap link: {url}")
                    found_links = re.findall(r"<loc>(.*?)</loc>", content)
                    to_check.extend(found_links)
        # Return the product links found in the sitemaps
        return self.product_links
    
    def get_product_links(self) -> List[str]:
        """
        Get all product links found in the sitemaps.
        """
        return self.product_links

    def _is_url_product(self, url: str) -> bool:
        """
        Check if the current url is likely a product link.

        Args:
            url (str): The url to check.

        Returns:
            bool: True if the link appears to be a product link, False otherwise.
        """
        # Common patterns for product links in e-commerce sitemaps
        product_keywords = ["product", "item", "prod", "detail", "goods"]
        # Check if any keyword is in the URL path (case-insensitive)
        path = url.lower()
        return any(keyword in path for keyword in product_keywords)

    def _is_url_sitemap(self, url: str) -> bool:
        """
        Check if the current url is another sitemap link.

        Args:
            url (str): The url to check.

        Returns:
            bool: True if the url appears to be a sitemap link, False otherwise.
        """
        # Common patterns for sitemap links
        sitemap_keywords = ["sitemap", "sitemap.xml", ".xml"]
        path = url.lower()
        return any(keyword in path for keyword in sitemap_keywords)

    def _fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch the content of a sitemap link based on method specified in config.

        Args:
            url (str): The sitemap link to fetch.

        Returns:
            Optional[str]: _description_
        """
        method = getattr(config, "METHOD", "requests")
        if method == "selenium":
            if not self.driver:
                self.driver = setup_driver()
            self.driver.get(url)
            return self.driver.page_source
        else:
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                return response.text
            except Exception:
                return None

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _extract_links(self, content: str) -> List[str]:
        try:
            # Remove XML declaration for easier parsing if present
            content = re.sub(r'<\?xml.*?\?>', '', content).strip()
            root = ET.fromstring(content)
            # Extract namespace if present
            ns_match = re.match(r'\{(.*)\}', root.tag)
            ns = {'ns': ns_match.group(1)} if ns_match else {}
            # Find all <loc> tags, with or without namespace
            if ns:
                locs = root.findall('.//ns:loc', ns)
            else:
                locs = root.findall('.//loc')
            return [loc.text for loc in locs if loc.text]
        except Exception:
            return []
