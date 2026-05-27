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
MAPPING_FILE = r"scripts\swiss_ticker_mapping.txt"

def clean_name(name):
    if not name: return ""
    name = str(name).lower().strip()
    for suffix in [" ag", " ltd", " sa", " inc", " plc", " group", " holding", " s.a.", " corp", " corporation", " limited", " india"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name.strip()

def get_row_val(row, candidates):
    for c in candidates:
        if c in row: return row[c]
        for k in row.keys():
            if k.strip().lower() == c.lower():
                return row[k]
    return None

def load_ticker_mapping():
    mapping = {} # cleaned_name -> ticker
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#'): continue
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    ticker = parts[1].strip().lower()
                    name = parts[3].strip()
                    mapping[clean_name(name)] = ticker
    return mapping

def load_csv_data():
    symbol_to_data = {}
    if not os.path.exists(CSV_PATH): return {}
    
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = get_row_val(row, ['symbol', 'ticker'])
                sector = get_row_val(row, ['sector_new', 'sector'])
                industry = get_row_val(row, ['industry_new', 'industry'])
                if symbol:
                    symbol_to_data[symbol.lower()] = {
                        "sector": sector,
                        "industry": industry
                    }
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return symbol_to_data

def enrich():
    db = SessionLocal()
    
    name_to_ticker = load_ticker_mapping()
    symbol_data = load_csv_data()
    
    print(f"Loaded {len(name_to_ticker)} manual mappings and {len(symbol_data)} symbols from CSV.")
    
    sources = db.query(JobSource).all()
    updated_count = 0
    
    for src in sources:
        cname = clean_name(src.name)
        ticker = name_to_ticker.get(cname)
        
        # Try fuzzy match on manual mapping
        if not ticker:
            close = get_close_matches(cname, list(name_to_ticker.keys()), n=1, cutoff=0.8)
            if close:
                ticker = name_to_ticker[close[0]]
        
        # If we have a ticker, get data from CSV
        if ticker in symbol_data:
            data = symbol_data[ticker]
            src.sector = data['sector']
            src.industry = data['industry']
            updated_count += 1
            print(f"Enriched {src.name} (Ticker: {ticker}): Sector={src.sector}, Industry={src.industry}")
        else:
            print(f"No ticker found for {src.name} or no data in CSV for {ticker}")
        
    db.commit()
    db.close()
    print(f"Enrichment complete. Updated {updated_count} sources.")

if __name__ == "__main__":
    enrich()
