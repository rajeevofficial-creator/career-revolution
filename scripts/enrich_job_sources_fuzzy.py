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
    """Clean company name for better matching (lowercase, no AG/Ltd/SA)."""
    if not name: return ""
    name = name.lower().strip()
    for suffix in [" ag", " ltd", " sa", " inc", " plc", " group", " holding", " s.a.", " corp", " corporation"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name

def load_csv_data():
    """Load name -> (Symbol, Sector, Industry) from CSV."""
    name_data = {} # clean_name -> {symbol, sector, industry}
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found at {CSV_PATH}")
        return {}
    
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                full_name = row.get('name')
                if full_name:
                    cname = clean_name(full_name)
                    name_data[cname] = {
                        "symbol": row.get('symbol'),
                        "sector": row.get('sector_new') or row.get('sector'),
                        "industry": row.get('industry_new') or row.get('industry')
                    }
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return name_data

def enrich():
    db = SessionLocal()
    
    csv_info = load_csv_data()
    print(f"Loaded {len(csv_info)} names from CSV.")
    
    sources = db.query(JobSource).all()
    updated_count = 0
    
    csv_names = list(csv_info.keys())
    
    for src in sources:
        target_name = clean_name(src.name)
        match = None
        
        # Exact match of cleaned name
        if target_name in csv_info:
            match = csv_info[target_name]
        else:
            # Simple substring match or close match
            close = get_close_matches(target_name, csv_names, n=1, cutoff=0.8)
            if close:
                match = csv_info[close[0]]
                
        if match:
            src.sector = match['sector']
            src.industry = match['industry']
            updated_count += 1
            print(f"Enriched {src.name}: Sector={src.sector}, Industry={src.industry} (Matched: {match['symbol']})")
        else:
            print(f"No match for {src.name} ({target_name})")
        
    db.commit()
    db.close()
    print(f"Enrichment complete. Updated {updated_count} sources.")

if __name__ == "__main__":
    enrich()
