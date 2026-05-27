import os
import re

search_dir = r"c:\Users\rajeev\career_revolution"
pattern = re.compile(r"rajeev\.sharma", re.IGNORECASE)

for root, dirs, files in os.walk(search_dir):
    if "venv" in root or ".git" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.bat') or file.endswith('.json'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            print(f"{filepath}:{i}: {line.strip()}")
            except Exception as e:
                pass
