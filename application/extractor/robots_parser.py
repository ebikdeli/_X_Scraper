import requests
from urllib.parse import urljoin
from typing import Dict, List, Optional, Tuple
from application.driver.chrome import restart_driver, setup_driver
from logger.logger import setup_logger
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
import config
import re
import xml.etree.ElementTree as ET


logger = setup_logger(__name__)


class RobotsTxtParser:
    """Parse robots.txt file for a domain or website
    """
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.robots_url = urljoin(self.base_url, '/robots.txt')
        self.user_agents: Dict[str, Dict[str, List[str]]] = {}
        self.sitemaps: List[str] = []
        self.driver: Optional[WebDriver] = None

    def scrape_robots(self) -> bool:
        """Scrape the robots.txt file using requests first, then Selenium if needed."""
        if self._scrape_requests():
            return True
        return self._scrape_selenium()

    def _scrape_requests(self) -> bool:
        """Attempt to fetch robots.txt using the requests library."""
        try:
            response = requests.get(self.robots_url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            self._parse_content(response.text)
            return True
        except requests.RequestException as e:
            logger.warning(f"Requests failed for robots.txt: {e}")
            return False

    def _scrape_selenium(self) -> bool:
        """Attempt to fetch robots.txt using Selenium."""
        try:
            if not self.driver:
                self.driver = setup_driver()
            self.driver.get(self.robots_url)
            self._parse_content(self.driver.page_source)
            return True
        except WebDriverException as e:
            logger.warning(f"Selenium driver failed for robots.txt; restarting once: {e}")
            try:
                self.driver = restart_driver()
                self.driver.get(self.robots_url)
                self._parse_content(self.driver.page_source)
                return True
            except Exception as retry_error:
                logger.error(f"Selenium retry failed for robots.txt: {retry_error}")
                return False
        except Exception as e:
            logger.error(f"Selenium failed for robots.txt: {e}")
            return False

    def _parse_content(self, content: str) -> None:
        """Parses the robots.txt content and assign values for 'user_agents' and 'sitemaps'"""
        # Read robots.txt line by line and parses each line to find if the line is for example a 'user_agent', 'sitemap'
        current_user_agents: List[str] = []
        for line in content.splitlines():
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Handle User-agent, Disallow, Allow, Sitemap
            # Every line in robots.txt is expected to be in the format: "directive: value"
            parts = line.strip().split(':', 1)
            if len(parts) != 2:
                continue
            # Split the line into directive and value, and process accordingly
            # for example: directive = 'user-agent', value = '*' or directive = 'disallow', value = '/private' or directive = 'sitemap', value = 'https://example.com/sitemap.xml' or directive = 'allow', value = '/public' or directive = 'user-agent', value = 'Googlebot'
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
    """Helper class that traverses sitemap URLs declared in robots.txt and collects product-like links.

    The parser is initialized with an instance of :class:`RobotsTxtParser`, which already
    contains the sitemap endpoints discovered from the robots file. This class then walks
    those sitemap URLs recursively, fetches their XML content, extracts nested links, and
    keeps track of URLs that look like product pages.

    Attributes:
        robots_parser: Parsed robots.txt data source used to obtain sitemap URLs.
        product_links: Accumulated list of product-like links found while traversing sitemaps.
    """
    def __init__(self, robots_parser: RobotsTxtParser) -> None:
        self.robots_parser = robots_parser
        self.product_links: List[str] = []
        self.driver: Optional[WebDriver] = None

    def find_product_sitemap_links(self) -> List[str]:
        """
        Traverse every sitemap discovered in robots.txt and collect product-like links.

        The method starts from the sitemap URLs declared in robots.txt, fetches their XML
        payloads, extracts nested <loc> entries, and recursively keeps following sitemap-like
        endpoints until no new links remain. URLs that look like product pages are appended
        to ``product_links`` while duplicates are ignored.

        Returns:
            List[str]: Unique product-like links found while traversing sitemaps.
        """
        to_check: List[str] = list(self.robots_parser.get_sitemaps())
        checked: set[str] = set()
        if not to_check:
            logger.warning("No sitemaps found in robots.txt.")
            return self.product_links
        logger.info(f"Starting with {len(to_check)} sitemap links to check.")
        # Use a breadth-first search approach to traverse all sitemap links
        # We maintain a queue of links to check and a set of already checked links to avoid cycles.
        while to_check:
            url = to_check.pop(0)
            if not url or url in checked:
                continue
            checked.add(url)
            logger.info(f"Checking sitemap link: {url}")
            if self._is_url_product(url):
                if url not in self.product_links:
                    self.product_links.append(url)
                logger.info(f"Found product link: {url}")
                continue
            # If the URL is not a product link, check if it is a sitemap link and fetch its content
            if not self._is_url_sitemap(url):
                continue
            # Fetch the content of the sitemap URL using the specified method (requests or selenium)
            content = self._fetch_content(url)
            if not content:
                logger.warning(f"Could not fetch sitemap content for: {url}")
                continue
            # Extract links from the sitemap content and add them to the queue for further checking
            logger.info(f"Fetching sitemap content for: {url}")
            found_links = self._extract_sitemap_links(content)
            for link in found_links:
                link = link.strip()
                if not link:
                    continue
                if link not in checked and link not in to_check:
                    to_check.append(link)
        # After traversing all sitemaps, return the list of unique product links found.
        return self.product_links
    
    def get_product_links(self) -> List[str]:
        """
        Return all the product links found in the sitemaps.
        """
        return self.product_links

    def _is_url_product(self, url: str) -> bool:
        """
        Check if the current url is likely a product link endpoint.

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
        path = url.lower()
        return path.endswith('.xml') or 'sitemap' in path

    def close(self) -> None:
        """Release this object's reference to the shared Selenium driver."""
        self.driver = None

    def _fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch the content of a sitemap link based on method specified in config.

        Args:
            url (str): The sitemap link to fetch.

        Returns:
            Optional[str]: _description_
        """
        if getattr(config, 'METHOD', 'requests') == "selenium":
            try:
                if not self.driver:
                    self.driver = setup_driver()
                self.driver.get(url)
                return self.driver.page_source
            except WebDriverException as e:
                logger.warning(f"Selenium driver failed for sitemap; restarting once: {e}")
                try:
                    self.driver = restart_driver()
                    self.driver.get(url)
                    return self.driver.page_source
                except Exception as retry_error:
                    logger.error(f"Selenium retry failed for sitemap")
                    print(f"Selenium retry failed for sitemap: {retry_error}")
                    return None
        else:
            try:
                response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.text
            except Exception:
                return None

    def _extract_links(self, content: str) -> List[str]:
        """Backward-compatible alias for sitemap link extraction."""
        return self._extract_sitemap_links(content)

    def _extract_sitemap_links(self, content: str) -> List[str]:
        """Extract sitemap URLs from XML sitemap content.

        The method first tries to parse the input as XML and collect all
        <loc> values. If parsing fails, it falls back to a regex-based
        URL extraction for plain-text or malformed sitemap content.

        Args:
            content (str): Raw sitemap content, usually XML. expected to contain <loc> elements. example: <urlset><url><loc>https://example.com/product1</loc></url></urlset>

        Returns:
            List[str]: A unique list of extracted sitemap URLs.
        """
        if not content:
            return []
        # Remove any XML declaration or processing instructions to avoid parsing issues
        content_clean = re.sub(
            r'<\?xml.*?\?>', '', content, flags=re.IGNORECASE | re.DOTALL
        ).strip()
        # Try to parse the cleaned content as XML and extract <loc> elements
        try:
            # Parse the XML content and handle namespaces if present
            root = ET.fromstring(content_clean)
            namespace = None
            if root.tag.startswith('{'):
                # Extract the namespace from the root tag if it exists
                # For example, if the root tag is '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset',
                # the namespace will be 'http://www.sitemaps.org/schemas/sitemap/0.9'
                namespace = root.tag[1:].split('}')[0]
            # Find all <loc> elements, considering the namespace if present, and collect their text values
            links: List[str] = []
            if namespace:
                locs = root.findall(f'.//{{{namespace}}}loc')
            else:
                locs = root.findall('.//loc')
            # Iterate through the found <loc> elements, extract their text content, and add them to the links list
            for loc in locs:
                url = (loc.text or '').strip()
                if url:
                    links.append(url)
            # Return a unique list of links by converting to a dict and back to a list
            return list(dict.fromkeys(links))
        # If XML parsing fails, fall back to regex-based URL extraction for plain-text or malformed sitemap content
        except ET.ParseError:
            # Fallback for malformed XML or plain-text sitemap content.
            url_pattern = r'https?://[^\s"<>\']+'
            links = re.findall(url_pattern, content_clean)
            return list(dict.fromkeys(links))


def start_extract_robots_links(url: str, method: Optional[str] = None) -> list[str]:
    """Start extracting robots.txt sitemap links and return product links found."""
    # Store the previous method in config to restore it later
    previous_method = getattr(config, 'METHOD', 'requests')
    if method:
        config.METHOD = method
    rtp = RobotsTxtParser(url)
    try:
        rtp.scrape_robots()
        rel = RobotsExtLinks(rtp)
        return rel.find_product_sitemap_links()
    finally:
        # Restore the previous method in config to avoid side effects for other parts of the application
        config.METHOD = previous_method
