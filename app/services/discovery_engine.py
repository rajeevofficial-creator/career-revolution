"""
Discovery Engine for Stage B of the Super-Agent v2.0 Pipeline.
Integrates with professional search APIs like Serper.dev and Tavily.
"""

import logging
import requests
import asyncio
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class SearchResult:
    """Standardized search result object."""
    def __init__(self, title: str, url: str, snippet: str, source: str, location: Optional[str] = None, source_db_id: Optional[int] = None):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.location = location
        self.source_db_id = source_db_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "location": self.location,
            "source_db_id": self.source_db_id
        }

class DiscoveryEngine:
    """Service for discovering job links using professional search APIs."""
    
    def __init__(self):
        self.serper_key = settings.serper_api_key
        self.tavily_key = settings.tavily_api_key
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def discover_links(self, queries: List[str], limit_per_query: int = 5, profile: Any = None) -> List[SearchResult]:
        """
        Executes discovery across multiple Boolean queries.
        Returns a deduplicated list of SearchResult objects.
        """
        all_results = []
        seen_urls = set()
        
        # Determine which engine to use
        engine_func = self._search_serper if self.serper_key else (self._search_tavily if self.tavily_key else self._search_fallback)
        
        logger.info(f"Using discovery engine: {engine_func.__name__}")
        
        for query in queries[:5]: # Limit to top 5 queries to save tokens/credits
            results = await engine_func(query, limit_per_query)
            for res in results:
                if res.url not in seen_urls:
                    all_results.append(res)
                    seen_urls.add(res.url)
            
            # Avoid rate limiting/bursts
            await asyncio.sleep(0.5)
            
        # EXTRA FALLBACK: If still no results and no API keys, try direct portal probing
        logger.info(f"Discovery phase finished. Results: {len(all_results)}. Profile provided: {profile is not None}")
        if not all_results and profile and not self.serper_key and not self.tavily_key:
            logger.info("Universal search failed/blocked (202/403). Attempting Direct Portal Probing...")
            direct_results = await self._search_direct_portals(profile.desired_job_title, profile.location or "Switzerland")
            for res in direct_results:
                if res.url not in seen_urls:
                    all_results.append(res)
                    seen_urls.add(res.url)
            
        return all_results

    async def _search_direct_portals(self, title: str, location: str) -> List[SearchResult]:
        """Probes major portals directly without search engine intermediates."""
        from app.services.search_service import SearchService
        svc = SearchService()
        
        portals = ["jobs.ch", "indeed"] # LinkedIn is usually too hard to scrape directly
        all_links = []
        
        for p in portals:
            links = await svc.search_portal_directly(p, title, location)
            for l in links:
                all_links.append(SearchResult(
                    title=f"Position on {p.capitalize()}",
                    url=l,
                    snippet=f"Discovered via direct {p} search.",
                    source=f"direct_{p}",
                    location=None
                ))
            await asyncio.sleep(1) # Be nice
            
        return all_links

    async def _search_serper(self, query: str, limit: int) -> List[SearchResult]:
        """Serper.dev (Google Search API) integration."""
        url = "https://google.serper.dev/search"
        # tbs=qdr:w restricts results to the last week
        payload = {"q": query, "num": limit, "tbs": "qdr:w"}
        headers = {
            'X-API-KEY': self.serper_key,
            'Content-Type': 'application/json'
        }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, headers=headers, timeout=10))
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('organic', []):
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        url=item.get('link', ''),
                        snippet=item.get('snippet', ''),
                        source="serper",
                        location=None # Serper doesn't provide structured location usually
                    ))
                return results
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
        return []

    async def _search_tavily(self, query: str, limit: int) -> List[SearchResult]:
        """Tavily search integration."""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
            "time_range": "week" # Restrict to last 7 days
        }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, timeout=10))
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('results', []):
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        url=item.get('url', ''),
                        snippet=item.get('content', ''), # Tavily uses content for snippet
                        source="tavily",
                        location=None
                    ))
                return results
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
        return []

    async def _search_fallback(self, query: str, limit: int) -> List[SearchResult]:
        """Fallback to internal scraping if no API keys are present."""
        logger.warning(f"No Search API key. Using DDG for: {query}")
        from app.services.search_service import SearchService
        svc = SearchService()
        
        links = await svc._ddg_search(query, limit)
        if not links:
            # Try a simpler version of the query if the Boolean one is too complex for DDG HTML
            # Strip site: and complex operators for DDG basic
            simple_query = query.replace('site:', '').replace('intitle:', '').replace('inurl:', '').replace('"', '').split('after:')[0].strip()
            logger.info(f"Retrying simpler query for DDG: {simple_query}")
            links = await svc._ddg_search(simple_query, limit)
            
        return [SearchResult(title="Discovery Result", url=link, snippet="Click to view details", source="fallback", location=None) for link in links]
