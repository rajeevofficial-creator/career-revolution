import sys
import os
import json
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, JobSource
from app.services.source_discovery import SourceDiscoveryService
from app.services.llm_analysis import LLMAnalysisService

# List of companies extracted from the image
SWISS_COMPANIES = [
    "ABB Ltd", "Novartis AG", "Roche Holding AG", "Nestle SA", "UBS Group AG",
    "Zurich Insurance Group AG", "Cie Financiere Richemont", "Givaudan SA",
    "Holcim Ltd", "Swiss Re AG", "Lonza Group AG", "Alcon Inc", "Sika AG",
    "Partners Group Holding AG", "Geberit AG", "Swisscom AG", "Sonova Holding AG",
    "Lindt & Spruengli AG", "Logitech International SA", "Straumann Holding AG",
    "VAT Group AG", "SIG Group AG", "Kuehne + Nagel International AG",
    "Barry Callebaut AG", "Julius Baer Group Ltd", "Schindler Holding AG",
    "Swatch Group AG", "Ems-Chemie Holding AG", "Temenos AG", "Adecco Group AG",
    "Belimo Holding AG", "Helvetia Holding AG", "BKW AG", "Galenica AG",
    "Cembra Money Bank AG", "PSP Swiss Property AG", "Allreal Holding AG",
    "Swiss Prime Site AG", "Mobimo Holding AG", "Intershop Holding AG",
    "Hiag Immobilien Holding AG", "Warteck Invest AG", "SF Urban Properties AG",
    "Novavest Real Estate AG", "Banque Cantonale Vaudoise", "St.Galler Kantonalbank AG",
    "Luzerner Kantonalbank AG", "Berner Kantonalbank AG", "Valiant Holding AG",
    "Hypothekarbank Lenzburg AG", "Graubuendner Kantonalbank", "Banque Cantonale du Jura SA",
    "Banque Cantonale de Geneve", "Banque Cantonale du Valais", "Banque Cantonale de Fribourg",
    "Zuger Kantonalbank", "Schaffhauser Kantonalbank", "Glarner Kantonalbank",
    "Obwaldner Kantonalbank", "Nidwaldner Kantonalbank", "Urner Kantonalbank",
    "Appenzeller Kantonalbank", "Walliser Kantonalbank"
]

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

async def import_companies():
    db = SessionLocal()
    llm = LLMAnalysisService()
    
    print(f"Starting import of {len(SWISS_COMPANIES)} Swiss companies...")
    
    # Pre-cache existing sources
    existing_sources = db.query(JobSource).all()
    normalized_map = {normalize_url(s.url): s for s in existing_sources}
    
    new_count = 0
    skipped_count = 0
    
    # We process in small batches to avoid hitting rate limits or timeouts
    batch_size = 5
    for i in range(0, len(SWISS_COMPANIES), batch_size):
        batch = SWISS_COMPANIES[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{len(SWISS_COMPANIES)//batch_size + 1}...")
        
        prompt = f"""
        Find the career/jobs portal URL for the following Swiss companies.
        Companies: {', '.join(batch)}
        
        Return ONLY a JSON array of objects with 'name', 'url', and 'description'.
        - 'name': The company name.
        - 'url': The specific career or jobs page URL (starting with https://).
        - 'description': A brief mention of the company (e.g., 'Major Swiss bank', 'Leading pharma company').
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
                        industry_focus='Various (Swiss List)',
                        location_focus='Switzerland',
                        quality_score=90, # High quality since it's a major company
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
                print(f"  Error: LLM response was not a list for batch {batch}")
        except Exception as e:
            print(f"  Error processing batch: {e}")
            
        db.commit()
        await asyncio.sleep(1) # Small delay
        
    db.close()
    print(f"Import complete. Added {new_count} new sources, skipped {skipped_count} duplicates.")

if __name__ == "__main__":
    asyncio.run(import_companies())
