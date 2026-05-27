import os

log_path = r"c:\Users\rajeev\career_revolution\server.log"
if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    print(f"Total lines in server.log: {len(lines)}")
    # Print the last 100 lines
    for line in lines[-100:]:
        print(line.strip())
else:
    print("server.log does not exist")
