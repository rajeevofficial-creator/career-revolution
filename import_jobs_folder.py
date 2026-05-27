"""
Import Jobs 2024 folder from flash drive to Career Revolution.
This script will copy career-related files and prepare them for upload.
"""

import os
import shutil
import json
from pathlib import Path

# Configuration
SOURCE_FOLDER = r"D:\Jobs 2024"
DEST_FOLDER = r"C:\Users\rajeev\.openclaw\workspace\career_revolution\jobs_import"
UPLOAD_READY_FOLDER = r"C:\Users\rajeev\.openclaw\workspace\career_revolution\upload_ready"

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.pdf': 'PDF Documents',
    '.doc': 'Word Documents',
    '.docx': 'Word Documents',
    '.txt': 'Text Files',
    '.png': 'Images',
    '.jpg': 'Images',
    '.jpeg': 'Images',
    '.pptx': 'Presentations',
    '.xlsx': 'Spreadsheets'
}

def categorize_file(filename):
    """Categorize files based on filename patterns."""
    filename_lower = filename.lower()
    
    if 'cv' in filename_lower or 'resume' in filename_lower:
        return 'CV/Resume'
    elif 'cover' in filename_lower:
        return 'Cover Letters'
    elif 'certif' in filename_lower or 'license' in filename_lower:
        return 'Certifications'
    elif 'transcript' in filename_lower:
        return 'Transcripts'
    elif 'reference' in filename_lower:
        return 'Reference Letters'
    elif 'passport' in filename_lower or 'ahv' in filename_lower or 'bank' in filename_lower:
        return 'Personal Documents'
    elif 'salary' in filename_lower or 'payroll' in filename_lower:
        return 'Salary Documents'
    elif 'photo' in filename_lower or 'picture' in filename_lower:
        return 'Photos'
    elif 'job' in filename_lower or 'application' in filename_lower:
        return 'Job Applications'
    elif 'contract' in filename_lower:
        return 'Contracts'
    else:
        return 'Other Career Documents'

def import_jobs_folder():
    """Import and organize Jobs 2024 folder."""
    
    print("=" * 60)
    print("IMPORTING JOBS 2024 FOLDER")
    print("=" * 60)
    
    # Check if source folder exists
    if not os.path.exists(SOURCE_FOLDER):
        print(f"ERROR: Source folder not found: {SOURCE_FOLDER}")
        print("Please make sure the flash drive is connected and the folder exists.")
        return
    
    print(f"Source: {SOURCE_FOLDER}")
    print(f"Destination: {DEST_FOLDER}")
    print(f"Upload Ready: {UPLOAD_READY_FOLDER}")
    print()
    
    # Create destination folders
    os.makedirs(DEST_FOLDER, exist_ok=True)
    os.makedirs(UPLOAD_READY_FOLDER, exist_ok=True)
    
    # Statistics
    stats = {
        'total_files': 0,
        'supported_files': 0,
        'unsupported_files': 0,
        'by_category': {},
        'by_extension': {}
    }
    
    # Walk through source folder
    print("Scanning files...")
    for root, dirs, files in os.walk(SOURCE_FOLDER):
        for file in files:
            stats['total_files'] += 1
            
            # Get file extension
            ext = os.path.splitext(file)[1].lower()
            
            # Check if supported
            if ext in SUPPORTED_EXTENSIONS:
                stats['supported_files'] += 1
                
                # Update extension stats
                if ext not in stats['by_extension']:
                    stats['by_extension'][ext] = 0
                stats['by_extension'][ext] += 1
                
                # Categorize file
                category = categorize_file(file)
                if category not in stats['by_category']:
                    stats['by_category'][category] = 0
                stats['by_category'][category] += 1
                
                # Source path
                src_path = os.path.join(root, file)
                
                # Create safe filename (remove special characters)
                safe_filename = file.replace(' ', '_').replace('(', '').replace(')', '')
                
                # Destination path in categorized folder
                category_folder = os.path.join(DEST_FOLDER, category)
                os.makedirs(category_folder, exist_ok=True)
                dest_path = os.path.join(category_folder, safe_filename)
                
                # Also copy to upload ready folder (flat structure)
                upload_ready_path = os.path.join(UPLOAD_READY_FOLDER, safe_filename)
                
                try:
                    # Copy to categorized folder
                    shutil.copy2(src_path, dest_path)
                    
                    # Copy to upload ready folder
                    shutil.copy2(src_path, upload_ready_path)
                    
                    if stats['supported_files'] <= 10:  # Show first 10 files
                        print(f"  [OK] {file} -> {category}")
                    
                except Exception as e:
                    print(f"  [ERROR] Error copying {file}: {e}")
            else:
                stats['unsupported_files'] += 1
    
    # Print summary
    print()
    print("=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"Total files scanned: {stats['total_files']}")
    print(f"Supported files: {stats['supported_files']}")
    print(f"Unsupported files: {stats['unsupported_files']}")
    print()
    
    print("Files by category:")
    for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count} files")
    
    print()
    print("Files by extension:")
    for ext, count in sorted(stats['by_extension'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {ext}: {count} files ({SUPPORTED_EXTENSIONS.get(ext, 'Unknown')})")
    
    print()
    print("IMPORTED FILES ARE READY FOR UPLOAD:")
    print(f"1. Organized files: {DEST_FOLDER}")
    print(f"2. Upload-ready files: {UPLOAD_READY_FOLDER}")
    print()
    print("NEXT STEPS:")
    print("1. Open dashboard.html in browser")
    print("2. Use 'Upload Folder' button")
    print("3. Select folder: upload_ready")
    print("4. Click 'Upload All Files'")
    print()
    print("=" * 60)
    
    # Save statistics
    stats_file = os.path.join(DEST_FOLDER, "import_stats.json")
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Statistics saved to: {stats_file}")

if __name__ == "__main__":
    import_jobs_folder()