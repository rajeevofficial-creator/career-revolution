"""
Run document processing automatically.
"""

import os
import sys
import subprocess

# Run the processing with automatic yes response
print("Running document processing...")

# Create a simple script that answers yes
script_content = '''
import sys
import io

# Redirect input to provide "yes"
sys.stdin = io.StringIO("yes\\n")

# Now import and run the main processing
from run_document_processing import main
main()
'''

# Write temporary script
with open("_temp_run.py", "w") as f:
    f.write(script_content)

# Run it
result = subprocess.run([sys.executable, "_temp_run.py"], 
                       capture_output=True, text=True, cwd=".")

# Print output
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Clean up
if os.path.exists("_temp_run.py"):
    os.remove("_temp_run.py")