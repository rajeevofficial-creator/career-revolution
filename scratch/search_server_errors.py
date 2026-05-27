import os
import re

log_path = r"c:\Users\rajeev\career_revolution\server.log"
pattern = re.compile(r"prepare", re.IGNORECASE)

if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, 1):
            if pattern.search(line):
                print(f"{i}: {line.strip()}")
else:
    print("server.log not found")
