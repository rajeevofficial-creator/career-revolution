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
    return name.strip()

def get_row_val(row, candidates):
    """Get value from row using multiple potential key variants."""
    for c in candidates:
        # Check exact, then case-insensitive, then stripped
        if c in row: return row[c]
        for k in row.keys():
            if k.strip().lower() == c.lower():
                return row[k]
    return None

def load_csv_data():
    """Load and index CSV data with EXTREME robustness for headers."""
    name_data = {} # clean_name -> data
    symbol_to_data = {} # symbol -> data
    
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found at {CSV_PATH}")
        return {}, {}
    
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # Log the keys actually found
            print(f"Detected Headers: {reader.fieldnames}")
            
            for row in reader:
                symbol = get_row_val(row, ['symbol', 'ticker'])
                sector = get_row_val(row, ['sector_new', 'sector'])
                industry = get_row_val(row, ['industry_new', 'industry'])
                
                data = {
                    "symbol": symbol,
                    "sector": sector,
                    "industry": industry
                }
                
                if symbol:
                    symbol_to_data[symbol.lower()] = data
                
                # Check description and name
                for col in ['description', 'name', 'full_name', 'company']:
                    val = get_row_val(row, [col])
                    if val:
                        # If description is a long summary, skip it, but keep short names
                        if len(val) < 150:
                            cname = clean_name(val)
                            if cname:
                                name_data[cname] = data
                            
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return name_data, symbol_to_data

def enrich():
    db = SessionLocal()
    
    name_map, symbol_map = load_csv_data()
    print(f"Loaded {len(name_map)} name-based keys and {len(symbol_map)} symbols.")
    
    if not name_map and not symbol_map:
        print("Empty maps. Check headers above.")
        db.close()
        return

    sources = db.query(JobSource).all()
    updated_count = 0
    name_keys = list(name_map.keys())
    
    for src in sources:
        cname = clean_name(src.name)
        match = name_map.get(cname)
        
        if not match:
            # Try fuzzy
            close = get_close_matches(cname, name_keys, n=1, cutoff=0.7)
            if close:
                match = name_map[close[0]]
                
        if match:
            src.sector = match['sector']
            src.industry = match['industry']
            updated_count += 1
            print(f"Enriched {src.name}: Sector={src.sector}, Industry={src.industry}")
        else:
            # Fallback for Swiss giants
            fb = None
            if "novartis" in cname: fb = symbol_map.get("novn")
            elif "abb" in cname: fb = symbol_map.get("abbn") or symbol_map.get("abb")
            elif "roche" in cname: fb = symbol_map.get("rog")
            elif "ubs" in cname: fb = symbol_map.get("ubsg")
            elif "nestle" in cname: fb = symbol_map.get("nesn")
            
            if fb:
                src.sector = fb['sector']
                src.industry = fb['industry']
                updated_count += 1
                print(f"Enriched {src.name} (Fallback): Sector={src.sector}, Industry={src.industry}")
            else:
                print(f"No match for {src.name}")
        
    db.commit()
    db.close()
    print(f"Enrichment complete. Updated {updated_count} sources.")

if __name__ == "__main__":
    enrich()
