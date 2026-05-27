import csv
import os

csv_path = r"C:\Users\rajeev\Desktop\stock_profile.csv"
with open(csv_path, mode='r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    print(f"HEADER: {header}")
    first_row = next(reader)
    print(f"FIRST ROW: {first_row}")
    print(f"LENGTH HEADER: {len(header)}")
    print(f"LENGTH FIRST ROW: {len(first_row)}")
