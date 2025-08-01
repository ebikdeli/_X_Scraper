import requests
from urllib.parse import urljoin
from typing import Dict, List, Optional, Tuple
from application.driver.chrome import setup_driver
from logger.logger import setup_logger
import config
import re


logger = setup_logger(__name__)


class RobotsTxtParser:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.robots_url = urljoin(self.base_url, '/robots.txt')
        self.user_agents: Dict[str, Dict[str, List[str]]] = {}
        self.sitemaps: List[str] = []
        self.driver = None

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
            print(f"Unknown scraping method: {chosen_method}")
            return
        try:
            scrape_func()
        except Exception as e:
            print(f"Error fetching robots.txt using '{chosen_method}': {e}")
    
    def _scrape_requests(self) -> None:
        """Scrapes the robots.txt file using requests module."""
        try:
            response = requests.get(self.robots_url, timeout=5)
            response.raise_for_status()
            self._parse_content(response.text)
        except requests.RequestException as e:
            print(f"Error fetching robots.txt: {e}")
    
    def _scrape_selenium(self) -> None:
        """Scrapes the robots.txt file using Selenium module."""
        try:
            self.driver = setup_driver()
            self.driver.get(self.robots_url)
            content = self.driver.page_source
            if not content:
                raise ValueError("No content found in robots.txt")
            self._parse_content(content)
        except Exception as e:
            print(f"Error fetching robots.txt with Selenium: {e}")

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


class RobotsExtLinks:
    def __init__(self, robots_parser: RobotsTxtParser) -> None:
        self.robots_parser = robots_parser
    
    def ext_sitemap_links(self):
        """
        Read all the sitemap links extracted from robots.
        If a link belongs to a product, add it to product_links.
        If a link belongs to another sitemap, add it to sitemap_links for further checking.
        Continue until no sitemap links remain to check.
        Returns:
            List[str]: All product links found in the sitemaps.
        """
        product_links: List[str] = []
        to_check: List[str] = self.robots_parser.get_sitemaps()
        checked: set[str] = set()
        if not to_check:
            logger.warning("No sitemaps found in robots.txt.")
            return product_links
        logger.info(f"Starting with {len(to_check)} sitemap links to check.")
        # Loop through the sitemap links to check for product links or more sitemaps
        while to_check:
            sm_link = to_check.pop(0)
            if sm_link in checked:
                continue
            checked.add(sm_link)
            logger.info(f"Checking sitemap link: {sm_link}")
            # Check if the link is a product link or another sitemap link
            if self._check_sm_product_link(sm_link):
                product_links.append(sm_link)
                logger.info(f"Found product link: {sm_link}")
            elif self._check_sm_link(sm_link):
                content = self._fetch_content(sm_link)
                if content:
                    # If the link is a sitemap, find all links in it
                    logger.info(f"Found sitemap link: {sm_link}")
                    found_links = re.findall(r"<loc>(.*?)</loc>", content)
                    to_check.extend(found_links)
        # Return the product links found in the sitemaps
        return product_links

    def _check_sm_product_link(self, sm_link: str) -> bool:
        """
        Check if the current sitemap link is likely a product link.

        Args:
            sm_link (str): The sitemap link to check.

        Returns:
            bool: True if the link appears to be a product link, False otherwise.
        """
        # Common patterns for product links in e-commerce sitemaps
        product_keywords = ["product", "item", "prod", "detail", "goods"]
        # Check if any keyword is in the URL path (case-insensitive)
        path = sm_link.lower()
        return any(keyword in path for keyword in product_keywords)
    
    def _check_sm_link(self, sm_link: str) -> bool:
        """
        Check if the current sitemap link is another sitemap link.

        Args:
            sm_link (str): The sitemap link to check.

        Returns:
            bool: True if the link appears to be a sitemap link, False otherwise.
        """
        # Common patterns for sitemap links
        sitemap_keywords = ["sitemap", "sitemap.xml", ".xml"]
        path = sm_link.lower()
        return any(keyword in path for keyword in sitemap_keywords)

    def _fetch_content(self, sm_link: str) -> Optional[str]:
        """
        Fetch the content of a sitemap link based on method specified in config.

        Args:
            sm_link (str): The sitemap link to fetch.

        Returns:
            Optional[str]: _description_
        """
        method = getattr(config, "METHOD", "requests")
        if method == "selenium":
            driver = setup_driver()
            driver.get(sm_link)
            content = driver.page_source
            driver.quit()
            return content
        else:
            try:
                response = requests.get(sm_link, timeout=5)
                response.raise_for_status()
                return response.text
            except Exception:
                return None
