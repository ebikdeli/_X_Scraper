import requests
from urllib.parse import urljoin
from typing import Dict, List, Optional, Tuple

class RobotsTxtParser:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.robots_url = urljoin(self.base_url, '/robots.txt')
        self.user_agents: Dict[str, Dict[str, List[str]]] = {}
        self.sitemaps: List[str] = []
        self._fetch_and_parse()

    def _fetch_and_parse(self) -> None:
        """Fetches and parses the robots.txt file."""
        try:
            response = requests.get(self.robots_url, timeout=5)
            response.raise_for_status()
            self._parse_content(response.text)
        except requests.RequestException as e:
            print(f"Error fetching robots.txt: {e}")

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

# Example Usage
if __name__ == "__main__":
    website_url = "https://www.google.com"  # Replace with any website
    parser = RobotsTxtParser(website_url)

    # Print all rules for all user-agents
    print(f"Rules for {website_url}:")
    for ua, rules in parser.user_agents.items():
        print(f"\nUser-agent: {ua}")
        print(f"  Allow: {rules['allow']}")
        print(f"  Disallow: {rules['disallow']}")

    # Check if a path is allowed
    test_path = "/search"
    test_ua = "Googlebot"
    print(f"\nCan '{test_ua}' access '{test_path}'? {parser.is_allowed(test_ua, test_path)}")

    # Print sitemaps
    print("\nSitemaps:", parser.get_sitemaps())