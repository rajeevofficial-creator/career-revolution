import sys
import os
import json
import asyncio
import csv
from datetime import datetime
from sqlalchemy.orm import Session

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, JobSource
from app.services.llm_analysis import LLMAnalysisService

# Hardcoded companies from the image (Switzerland focus)
IMAGE_COMPANIES = [
    "ABB Ltd", "Novartis AG", "Roche Holding AG", "Nestle SA", "UBS Group AG",
    "Zurich Insurance Group AG", "Cie Financiere Richemont", "Givaudan SA",
    "Holcim Ltd", "Swiss Re AG", "Lonza Group AG", "Alcon Inc", "Sika AG",
    "Partners Group Holding AG", "Geberit AG", "Swisscom AG", "Sonova Holding AG",
    "Lindt & Spruengli AG", "Logitech International SA", "Straumann Holding AG",
    "VAT Group AG", "SIG Group AG", "Kuehne + Nagel International AG",
    "Barry Callebaut AG", "Julius Baer Group Ltd", "Schindler Holding AG",
    "Swatch Group AG", "Ems-Chemie Holding AG", "Temenos AG", "Adecco Group AG"
]

CSV_PATH = r"C:\Users\rajeev\Desktop\stock_profile.csv"
TARGET_COUNTRIES = ["Switzerland", "United States", "India"]

def normalize_url(url):
    if not url: return ""
    url = url.lower().strip()
    for prefix in ['https://', 'http://']:
        if url.startswith(prefix):
            url = url[len(prefix):]
    if url.startswith('www.'):
        url = url[4:]
    for subpath in ['/jobs', '/careers', '/vacancies', '/en', '/de', '/fr', '/it']:
        if url.endswith(subpath):
            url = url[:-len(subpath)]
        if subpath + '/' in url:
            url = url.replace(subpath + '/', '/')
    if url.endswith('/'):
        url = url[:-1]
    return url

def load_companies_from_csv():
    companies = []
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found at {CSV_PATH}")
        return []
    
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                country = row.get('country') or ""
                name = row.get('name') or ""
                # Check if country matches any of our targets (partial match ok)
                if name and any(target.lower() in country.lower() for target in TARGET_COUNTRIES):
                    companies.append({
                        "name": name,
                        "website": row.get('website'),
                        "country": country
                    })
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return companies

async def import_portals():
    db = SessionLocal()
    llm = LLMAnalysisService()
    
    csv_companies = load_companies_from_csv()
    print(f"Loaded {len(csv_companies)} companies from CSV for {TARGET_COUNTRIES}")
    
    # Combine with image companies
    all_targets = []
    for c in IMAGE_COMPANIES:
        all_targets.append({"name": c, "website": None, "country": "Switzerland"})
    
    # Add CSV companies, avoiding duplicates by name for now
    seen_names = set(c.lower() for c in IMAGE_COMPANIES)
    for c in csv_companies:
        name = c.get('name')
        if name and name.lower() not in seen_names:
            all_targets.append(c)
            seen_names.add(name.lower())

    print(f"Total unique companies to process: {len(all_targets)}")
    
    # Pre-cache existing sources
    existing_sources = db.query(JobSource).all()
    normalized_map = {normalize_url(s.url): s for s in existing_sources}
    
    new_count = 0
    skipped_count = 0
    
    # Process in batches
    batch_size = 5
    for i in range(0, len(all_targets), batch_size):
        batch = all_targets[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{len(all_targets)//batch_size + 1}...")
        
        # Build prompt with website context if available
        comp_details = []
        for c in batch:
            detail = f"- {c['name']} (Country: {c['country']}"
            if c['website']: detail += f", Website: {c['website']}"
            detail += ")"
            comp_details.append(detail)
            
        prompt = f"""
        Find the career/jobs portal URL for the following companies.
        Companies:
        {chr(10).join(comp_details)}
        
        Return ONLY a JSON array of objects with 'name', 'url', and 'description'.
        - 'name': The company name.
        - 'url': The specific career or jobs page URL (starting with https://).
        - 'description': A brief mention of the company (e.g., 'Major tech firm in USA', 'Swiss pharma leader').
        """
        
        try:
            response = await llm._get_gemini_response(prompt)
            if isinstance(response, list):
                for item in response:
                    url = item.get('url')
                    if not url: continue
                    
                    norm = normalize_url(url)
                    if norm in normalized_map:
                        print(f"  Skipping duplicate: {item['name']} ({url})")
                        skipped_count += 1
                        continue
                    
                    new_src = JobSource(
                        name=item['name'],
                        url=url,
                        source_type='company_career_page',
                        industry_focus='Stock Multi-Reginal',
                        location_focus='Multi-Regional',
                        quality_score=95,
                        description=item.get('description', ''),
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(new_src)
                    db.flush()
                    normalized_map[norm] = new_src
                    new_count += 1
                    print(f"  Added: {item['name']} -> {url}")
            else:
                print(f"  Error: LLM response was not a list for batch {i//batch_size}")
        except Exception as e:
            print(f"  Error processing batch: {e}")
            
        db.commit()
        await asyncio.sleep(2) # Protect API limits
        
        # LIMIT for initial run to avoid massive bill/time
        if new_count >= 50:
            print("Reached 50 new sources limit for this run. Stopping.")
            break
        
    db.close()
    print(f"Import complete. Added {new_count} new sources, skipped {skipped_count} duplicates.")

if __name__ == "__main__":
    asyncio.run(import_portals())
