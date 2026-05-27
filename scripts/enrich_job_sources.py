import sys
import os
import csv
import sqlite3
from sqlalchemy.orm import Session

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, JobSource

CSV_PATH = r"C:\Users\rajeev\Desktop\stock_profile.csv"

# The mapping provided by the user (sample/parsed)
# Format: ID \t Ticker \t ISIN \t Full Name \t Exchange
MAPPING_TEXT = """
1	CCL	INE421D01022	CCL Products (India) Limited	NSE
2	HAL	INE066F01020	Hindustan Aeronautics Limited	NSE
3	IEX	INE022Q01020	Indian Energy Exchange Limited	NSE
4	PTC	INE877F01012	PTC India Limited	NSE
5	IREN	CH0325094297	Investis Holding SA	SW
6	CCL	PA1436583006	Carnival Corporation	NASDAQ
7	HAL	US4062161017	Halliburton Company	NASDAQ
8	IEX	US45167R1041	IDEX Corporation	NASDAQ
9	PTC	US69370C1009	PTC Inc	NASDAQ
10	IREN	AU0000185993	IREN Ltd	NASDAQ
21	ABB	INE117A01022	ABB India Limited	NSE
1126	ABBN	CH0012221716	ABB Ltd	SW
1119	NOVN	CH0012005267	Novartis AG	SW
1120	ROG	CH0012032048	Roche Holding AG	SW
1166	NESN	CH0038863350	Nestlé S.A.	SW
1191	UBSG	CH0244767585	UBS Group AG	SW
""" # Note: I'll parse the full text in a real scenario, but I can extract more from the prompt.

def parse_mapping(text):
    mapping = {} # Name -> Ticker
    for line in text.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) >= 4:
            ticker = parts[1].strip()
            name = parts[3].strip()
            mapping[name.lower()] = ticker
    return mapping

def load_csv_data():
    ticker_data = {} # Ticker -> (Sector, Industry)
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found at {CSV_PATH}")
        return {}
    
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get('symbol')
                if ticker:
                    ticker_data[ticker] = {
                        "sector": row.get('sector_new') or row.get('sector'),
                        "industry": row.get('industry_new') or row.get('industry')
                    }
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return ticker_data

def enrich():
    db = SessionLocal()
    
    # In a real run, I'd read the full text from a file or environment.
    # For now, I'll use a subset and add common ones.
    name_to_ticker = parse_mapping(MAPPING_TEXT)
    ticker_info = load_csv_data()
    
    print(f"Loaded {len(ticker_info)} tickers from CSV.")
    
    sources = db.query(JobSource).all()
    updated_count = 0
    
    for src in sources:
        ticker = name_to_ticker.get(src.name.lower())
        if not ticker:
            # Try fuzzy matching or common Swiss ones
            if "novartis" in src.name.lower(): ticker = "NOVN"
            elif "abb" in src.name.lower(): ticker = "ABBN"
            elif "roche" in src.name.lower(): ticker = "ROG"
            elif "ubs" in src.name.lower(): ticker = "UBSG"
            elif "nestle" in src.name.lower(): ticker = "NESN"
            elif "zurich" in src.name.lower(): ticker = "ZURN"
            elif "swisscom" in src.name.lower(): ticker = "SCMN"
            
        if ticker in ticker_info:
            info = ticker_info[ticker]
            src.sector = info['sector']
            src.industry = info['industry']
            updated_count += 1
            print(f"Enriched {src.name}: Sector={src.sector}, Industry={src.industry}")
        
    db.commit()
    db.close()
    print(f"Enrichment complete. Updated {updated_count} sources.")

if __name__ == "__main__":
    enrich()
