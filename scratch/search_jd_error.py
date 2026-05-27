import os
import re

search_dir = r"c:\Users\rajeev\career_revolution"
pattern = re.compile(r"_showDescriptionRequiredError", re.IGNORECASE)

for root, dirs, files in os.walk(search_dir):
    if "venv" in root or ".git" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(('.py', '.js', '.html', '.css', '.json')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            print(f"{filepath}:{i}: {line.strip()}")
            except Exception as e:
                pass
