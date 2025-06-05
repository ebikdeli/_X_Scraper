import re
import aiohttp
from urllib.parse import urljoin
from typing import Dict, List, Optional, Set, Tuple
import asyncio

class AsyncRobotsTxtParser:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.robots_url = urljoin(self.base_url, '/robots.txt')
        self.user_agents: Dict[str, Dict[str, Set[str]]] = {}
        self.sitemaps: Set[str] = set()
        self._regex_cache: Dict[str, re.Pattern] = {}  # Cache compiled regex patterns

    async def fetch(self) -> None:
        """Asynchronously fetches and parses robots.txt."""
        try:
            async with aiohttp.ClientSession() as session:
                # async with session.get(self.robots_url, timeout=5) as response:
                async with session.get(self.robots_url) as response:
                    response.raise_for_status()
                    content = await response.text()
                    await self._parse_content(content)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Error fetching robots.txt: {e}")

    async def _parse_content(self, content: str) -> None:
        """Parses robots.txt content with async support."""
        current_user_agents: List[str] = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            directive, value = parts[0].strip().lower(), parts[1].strip()
            if directive == 'user-agent':
                current_user_agents = [ua.strip() for ua in value.split(',') if ua.strip()]
                for ua in current_user_agents:
                    if ua not in self.user_agents:
                        self.user_agents[ua] = {'allow': set(), 'disallow': set()}
            elif directive in ('allow', 'disallow'):
                if not current_user_agents:
                    continue
                for ua in current_user_agents:
                    self.user_agents[ua][directive].add(value)
            elif directive == 'sitemap':
                self.sitemaps.add(value)

    def _path_to_regex(self, path: str) -> re.Pattern:
        """Converts a robots.txt path rule to a regex pattern."""
        if path in self._regex_cache:
            return self._regex_cache[path]
        # Escape regex chars and handle wildcards (*) and end-of-path ($)
        regex = re.escape(path)
        regex = regex.replace(r'\*', '.*')  # * → .*
        if path.endswith('$'):
            regex = regex[:-2] + '$'  # Exact match for paths ending with $
        else:
            regex += '.*'  # Default: prefix match
        compiled = re.compile(f'^{regex}')
        self._regex_cache[path] = compiled
        return compiled

    async def is_allowed(self, user_agent: str, path: str) -> bool:
        """Checks if a path is allowed for the given user-agent using regex matching."""
        path = path.lstrip('/')
        for ua in [user_agent, '*']:
            if ua not in self.user_agents:
                continue
            rules = self.user_agents[ua]
            # Check disallowed paths (most specific first)
            for disallowed in sorted(rules['disallow'], key=len, reverse=True):
                if disallowed and self._path_to_regex(disallowed.lstrip('/')).match(path):
                    # Check if an Allow rule overrides this Disallow
                    for allowed in rules['allow']:
                        if allowed and self._path_to_regex(allowed.lstrip('/')).match(path):
                            return True
                    return False
        return True  # Default: allowed

    async def get_sitemaps(self) -> List[str]:
        """Returns all sitemap URLs."""
        return list(self.sitemaps)

    async def get_rules(self, user_agent: str = '*') -> Optional[Dict[str, List[str]]]:
        """Returns rules for a specific user-agent."""
        if user_agent in self.user_agents:
            return {k: list(v) for k, v in self.user_agents[user_agent].items()}
        return None

# Example Usage
async def main():
    website_url = "https://www.google.com"  # Replace with any website
    parser = AsyncRobotsTxtParser(website_url)
    await parser.fetch()

    # Print rules for all user-agents
    print(f"Rules for {website_url}:")
    for ua, rules in parser.user_agents.items():
        print(f"\nUser-agent: {ua}")
        print(f"  Allow: {rules['allow']}")
        print(f"  Disallow: {rules['disallow']}")

    # Test path permissions
    test_cases = [
        ("Googlebot", "/search"),
        ("*", "/admin"),
        ("Bingbot", "/images/logo.jpg"),
    ]
    for ua, path in test_cases:
        is_allowed = await parser.is_allowed(ua, path)
        print(f"\nCan '{ua}' access '{path}'? {'Yes' if is_allowed else 'No'}")

    # Print sitemaps
    print("\nSitemaps:", await parser.get_sitemaps())

if __name__ == "__main__":
    asyncio.run(main())