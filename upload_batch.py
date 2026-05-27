"""
Upload a batch of files from upload_ready folder to simulate user upload.
"""

import os
import shutil
from pathlib import Path

def upload_batch_files(user_id=1, count=20):
    """Upload a batch of files to user's upload directory."""
    
    source_dir = "upload_ready"
    target_dir = f"uploads/{user_id}/resume"
    
    # Create target directory
    os.makedirs(target_dir, exist_ok=True)
    
    # Get list of files
    files = []
    for file in os.listdir(source_dir):
        if os.path.isfile(os.path.join(source_dir, file)):
            files.append(file)
    
    # Take first 'count' files
    files_to_upload = files[:count]
    
    print(f"Uploading {len(files_to_upload)} files to user {user_id}...")
    
    uploaded_count = 0
    for filename in files_to_upload:
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)
        
        try:
            shutil.copy2(source_path, target_path)
            uploaded_count += 1
            print(f"  [OK] {filename}")
        except Exception as e:
            print(f"  [ERROR] {filename}: {e}")
    
    print(f"\nUpload complete: {uploaded_count}/{len(files_to_upload)} files uploaded.")
    
    # Create a simple text file with file list
    list_file = os.path.join(target_dir, "_uploaded_files.txt")
    with open(list_file, 'w', encoding='utf-8') as f:
        f.write("Uploaded files:\n")
        for filename in files_to_upload:
            f.write(f"- {filename}\n")
    
    return uploaded_count

if __name__ == "__main__":
    # Upload 20 files for demonstration
    uploaded = upload_batch_files(user_id=1, count=20)
    print(f"\nReady to process {uploaded} files.")