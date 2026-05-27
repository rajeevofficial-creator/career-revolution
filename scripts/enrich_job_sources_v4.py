import sys
import os
import csv
import sqlite3
from difflib import get_close_matches
from sqlalchemy.orm import Session

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, JobSource

CSV_PATH = r"C:\Users\rajeev\Desktop\stock_profile.csv"

def clean_name(name):
    """Clean company name for better matching."""
    if not name: return ""
    name = str(name).lower().strip()
    # Remove common stock suffixes
    for suffix in [" ag", " ltd", " sa", " inc", " plc", " group", " holding", " s.a.", " corp", " corporation", " limited", " india"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    # Also handle " - " and "/"
    if " - " in name: name = name.split(" - ")[0]
    if "/" in name: name = name.split("/")[0]
    return name.strip()

def find_best_col(cols, candidates):
    for c in candidates:
        if c in cols: return c
    return None

def load_csv_data():
    """Load and index CSV data by various possible match keys."""
    indexed_data = {} # clean_name -> data
    symbol_to_data = {} # symbol -> data
    
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found at {CSV_PATH}")
        return {}, {}
    
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames: return {}, {}
            
            # Identify columns
            name_cols = [c for c in fieldnames if c in ['description', 'name', 'full_name']]
            symbol_col = find_best_col(fieldnames, ['symbol', 'ticker'])
            sector_col = find_best_col(fieldnames, ['sector_new', 'sector'])
            industry_col = find_best_col(fieldnames, ['industry_new', 'industry'])
            
            for row in reader:
                data = {
                    "symbol": row.get(symbol_col),
                    "sector": row.get(sector_col),
                    "industry": row.get(industry_col)
                }
                
                # Index by symbol
                if data['symbol']:
                    symbol_to_data[data['symbol'].lower()] = data
                
                # Index by all name-like columns
                for col in name_cols:
                    val = row.get(col)
                    if val:
                        cname = clean_name(val)
                        if cname:
                            indexed_data[cname] = data
                            
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return indexed_data, symbol_to_data

def enrich():
    db = SessionLocal()
    
    name_map, symbol_map = load_csv_data()
    if not name_map and not symbol_map:
        print("FAILED to load any data from CSV. Enrichment aborted.")
        db.close()
        return

    print(f"Loaded {len(name_map)} name-based keys and {len(symbol_map)} symbols.")
    
    sources = db.query(JobSource).all()
    updated_count = 0
    
    name_keys = list(name_map.keys())
    
    for src in sources:
        # 1. Try exact symbol match if we have it? (We don't usually)
        # 2. Try cleaned name match
        cname = clean_name(src.name)
        match = name_map.get(cname)
        
        # 3. Try fuzzy name match
        if not match:
            close = get_close_matches(cname, name_keys, n=1, cutoff=0.7)
            if close:
                match = name_map[close[0]]
                
        # 4. Special manual mapping for common portals
        if not match:
            if "novartis" in cname: match = symbol_map.get("novn")
            elif "abb" in cname: match = symbol_map.get("abbn") or symbol_map.get("abb")
            elif "roche" in cname: match = symbol_map.get("rog")
            elif "ubs" in cname: match = symbol_map.get("ubsg")
            elif "nestle" in cname: match = symbol_map.get("nesn")
            elif "swisscom" in cname: match = symbol_map.get("scmn")
            elif "zurich" in cname: match = symbol_map.get("zurn")
            
        if match:
            src.sector = match['sector']
            src.industry = match['industry']
            updated_count += 1
            print(f"Enriched {src.name}: Sector={src.sector}, Industry={src.industry}")
        else:
            print(f"No match for {src.name}")
        
    db.commit()
    db.close()
    print(f"Enrichment complete. Updated {updated_count} sources.")

if __name__ == "__main__":
    enrich()
