"""Test what LinkedIn actually returns during ingestion."""
import asyncio, sys, logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def main():
    from app.services.ingestion_service import IngestionService
    svc = IngestionService()

    url = "https://www.linkedin.com/jobs/search/?geoId=106693272"
    print(f"\nFetching: {url}")
    print("=" * 60)

    # Step 1: plain requests
    html = await svc._fetch_html_requests(url)
    print(f"Step 1 (requests): {len(html)} bytes")
    if html:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else "(no title)"
        print(f"  Page title: {title}")
        links = soup.find_all("a", href=True)
        print(f"  Total links found: {len(links)}")
        # Show first few links
        for a in links[:5]:
            print(f"    [{a.get_text()[:40].strip()}] -> {a['href'][:60]}")

    # Step 2: parse what we get
    results, next_pages = svc._parse_job_links(html, url, "LinkedIn Switzerland", set())
    print(f"\nStep 2 (parse): {len(results)} job links, {len(next_pages)} next pages")
    for r in results[:10]:
        print(f"  {r.title[:70]}")
        print(f"  -> {r.url[:70]}")

    # Step 3: Full ingest (may trigger Playwright/Firecrawl)
    print("\nStep 3: Full ingest (with Playwright fallback)...")
    all_results = await svc.ingest_from_source(
        "LinkedIn Switzerland", url, "job_portal", location_filter="Switzerland"
    )
    print(f"Total results from ingest: {len(all_results)}")
    for r in all_results[:10]:
        print(f"  {r.title[:70]}")
        print(f"  -> {r.url[:60]}")

asyncio.run(main())
