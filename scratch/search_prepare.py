import os
import re

search_dir = r"c:\Users\rajeev\career_revolution\app"
pattern = re.compile(r"/prepare", re.IGNORECASE)

for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            print(f"{filepath}:{i}: {line.strip()}")
            except Exception as e:
                pass
