import os
import re

filepath = r"c:\Users\rajeev\career_revolution\app\models\database.py"
pattern = re.compile(r"class LinkedInSession", re.IGNORECASE)

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if pattern.search(line):
                print(f"{filepath}:{i}: {line.strip()}")
except Exception as e:
    print(e)
