"""
Search Service for Career Revolution.
Finds real, live job URLs for specific occupations and locations.
"""

import logging
import requests
import asyncio
from typing import List, Dict, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class SearchService:
    """Service for discovering job links via web search."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key # For future Serper/Tavily integration
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def search_job_links(self, site_url: str, title: str, location: str, limit: int = 5) -> List[str]:
        """
        Searches for specific job links on a target site.
        Example: site:jobs.ch "IT Director" Basel
        """
        query = f'site:{site_url} "{title}" {location}'
        logger.info(f"Searching web for: {query}")
        
        # In a real production app, use Serper/Tavily/Google Search API.
        # Here we implement a robust fallback using DuckDuckGo (less aggressive blocking).
        try:
            links = await self._ddg_search(query, limit)
            if not links:
                # Fallback to a broader search if site-specific fails
                query_broad = f'"{title}" jobs {location} {site_url.split("//")[-1].split("/")[0]}'
                links = await self._ddg_search(query_broad, limit)
            
            return links
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def _ddg_search(self, query: str, limit: int) -> List[str]:
        """DuckDuckGo simple HTML search fallback."""
        try:
            # Try primary HTML endpoint then fallback
            endpoints = [
                f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
                f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            ]
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://duckduckgo.com/",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = None
            for url in endpoints:
                try:
                    logger.info(f"Trying DDG endpoint: {url}")
                    loop = asyncio.get_event_loop()
                    resp = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=3))
                    if resp.status_code == 200:
                        response = resp
                        break
                    logger.warning(f"DDG endpoint {url} returned {resp.status_code}")
                except Exception as e:
                    logger.error(f"DDG endpoint {url} failed: {e}")
            
            if not response:
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            # Results are usually at /y.js or inside links with specific formatting
            # Looking for links starting with target site or looking like job links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                # Filter results that look like real websites, not DDG internals or ad links
                if '/l/?kh=' in href: # Proxy link format check
                    actual_url = href.split('uddg=')[-1].split('&')[0]
                    actual_url = requests.utils.unquote(actual_url)
                    if actual_url.startswith('http') and 'duckduckgo.com' not in actual_url:
                        links.append(actual_url)
                elif href.startswith('http') and 'duckduckgo.com' not in href:
                    links.append(href)
                
                if len(links) >= limit:
                    break
            
            return links
        except Exception as e:
            logger.error(f"DDG scrape error: {e}")
            return []

    async def search_portal_directly(self, portal: str, title: str, location: str) -> List[str]:
        """Scrapes major portals directly using their internal search URLs."""
        from urllib.parse import quote_plus
        
        # Clean location for jobs.ch
        loc = location if location and location != "Switzerland" else ""
        
        endpoints = {
            "jobs.ch": f"https://www.jobs.ch/en/vacancies/?term={quote_plus(title)}&location={quote_plus(loc)}",
            "indeed": f"https://www.indeed.com/jobs?q={quote_plus(title)}&l={quote_plus(location)}",
            "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(title)}&location={quote_plus(location)}"
        }
        
        url = endpoints.get(portal)
        if not url: return []
        
        logger.info(f"Direct Portal Probe: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/"
        }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=15))
            
            if response.status_code != 200:
                logger.warning(f"Direct probe for {portal} returned {response.status_code}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            # Very basic link extraction for common portals
            if portal == "jobs.ch":
                # Look for all vacancy detail links
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/vacancies/detail/' in href:
                        full_url = f"https://www.jobs.ch{href}" if href.startswith('/') else href
                        # Split at ? to remove tracking params if any
                        links.append(full_url.split('?')[0])
            elif portal == "indeed":
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '')
                    if '/rc/clk' in href or '/viewjob' in href:
                        links.append(f"https://www.indeed.com{href}" if href.startswith('/') else href)
            
            unique_links = list(dict.fromkeys(links))
            logger.info(f"Direct probe for {portal} extracted {len(unique_links)} unique links.")
            return unique_links[:10]
        except Exception as e:
            logger.error(f"Direct probe error for {portal}: {e}")
            return []
