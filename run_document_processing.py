"""
Run document processing for Career Revolution.
This will process all uploaded documents and create AI-powered repository.
"""

import os
import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_processing():
    """Run the complete document processing pipeline."""
    print("="*80)
    print("CAREER REVOLUTION - AI DOCUMENT PROCESSING")
    print("="*80)
    
    # Check if uploads directory exists
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        print("ERROR: No uploads directory found.")
        print("Please upload documents first using the dashboard.")
        return
    
    # Find user directories
    user_dirs = []
    for item in os.listdir(uploads_dir):
        item_path = os.path.join(uploads_dir, item)
        if os.path.isdir(item_path) and item.isdigit():
            user_dirs.append((int(item), item_path))
    
    if not user_dirs:
        print("ERROR: No user documents found in uploads directory.")
        print("Please upload documents first using the dashboard.")
        return
    
    print(f"Found {len(user_dirs)} user(s) with documents.")
    
    # Import and run processor
    try:
        # Try to import the processor
        from document_processor import DocumentProcessor
        
        # Process each user
        for user_id, user_path in user_dirs:
            print(f"\n{'='*60}")
            print(f"PROCESSING USER {user_id}")
            print(f"{'='*60}")
            
            # Count documents
            doc_count = 0
            for root, dirs, files in os.walk(user_path):
                doc_count += len(files)
            
            print(f"Found {doc_count} document(s) for user {user_id}")
            
            if doc_count == 0:
                print("Skipping - no documents found.")
                continue
            
            # Ask for confirmation
            response = input(f"\nProcess {doc_count} document(s) for user {user_id}? (yes/no): ")
            if response.lower() != 'yes':
                print("Skipping user.")
                continue
            
            # Create processor and process
            processor = DocumentProcessor()
            result = processor.process_user_documents(user_id)
            
            # Display results
            print(f"\n{'='*60}")
            print(f"RESULTS FOR USER {user_id}")
            print(f"{'='*60}")
            
            if result['status'] == 'success':
                print(f"✅ SUCCESS: Processed {result['processed_count']} documents")
                
                profile = result['profile']
                consolidated = profile['consolidated_data']
                
                print(f"\n📊 PROFILE EXTRACTED:")
                print(f"   • Personal Info: {consolidated.get('personal_info', {}).get('name', 'Not found')}")
                print(f"   • Skills: {len(consolidated.get('skills', []))} skills")
                print(f"   • Experiences: {len(consolidated.get('experiences', []))} positions")
                print(f"   • Certifications: {len(consolidated.get('certifications', []))} certifications")
                
                analysis = result['analysis']
                print(f"\n📈 ANALYSIS:")
                print(f"   • Profile Strength: {analysis['summary'].get('profile_strength', 'Unknown')}")
                print(f"   • Completeness: {analysis['statistics'].get('profile_completeness', 0)}%")
                
                if analysis.get('recommendations'):
                    print(f"\n💡 TOP RECOMMENDATIONS:")
                    for i, rec in enumerate(analysis['recommendations'][:3], 1):
                        print(f"   {i}. [{rec['priority'].upper()}] {rec['action']}")
                
                print(f"\n📁 REPOSITORY CREATED:")
                print(f"   Location: {result['repository_path']}")
                print(f"   Files: profile.json, extracted/*.json, analysis/*.json")
                
                # Save processing report
                report_file = os.path.join(result['repository_path'], 'processing_report.json')
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'processing_date': result['profile']['generated_date'],
                        'summary': {
                            'processed_documents': result['processed_count'],
                            'issues': result['issue_count'],
                            'profile_completeness': analysis['statistics'].get('profile_completeness', 0)
                        }
                    }, f, indent=2)
                print(f"   Report: {report_file}")
                
            else:
                print(f"❌ FAILED: {result.get('message', 'Unknown error')}")
                if result.get('issues'):
                    print(f"\nIssues found:")
                    for issue in result['issues'][:5]:
                        print(f"   • {issue['file']}: {issue['error']}")
            
            print(f"\n{'='*60}")
    
    except ImportError as e:
        print(f"ERROR: Could not import document processor: {e}")
        print("\nRequired packages:")
        print("  pip install PyPDF2 python-docx Pillow pytesseract")
        return
    except Exception as e:
        print(f"ERROR: Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Review the generated repository in the 'repository' folder")
    print("2. Check the analysis and recommendations")
    print("3. Use the extracted data to build your career profile")
    print("4. Implement AI-powered features based on the structured data")
    print("\nYour career documents have been transformed into an AI-ready repository! 🚀")


def check_dependencies():
    """Check if required packages are installed."""
    print("Checking dependencies...")
    
    required_packages = [
        ('PyPDF2', 'PyPDF2'),
        ('python-docx', 'docx'),
        ('Pillow', 'PIL'),
        ('pytesseract', 'pytesseract')
    ]
    
    missing = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"  [OK] {package_name}")
        except ImportError:
            print(f"  [MISSING] {package_name} (missing)")
            missing.append(package_name)
    
    return missing


if __name__ == "__main__":
    print("Career Revolution - Document Processing System")
    print("Version 1.0 - AI-Powered Career Profile Builder")
    print()
    
    # Check dependencies
    missing = check_dependencies()
    
    if missing:
        print(f"\nMissing {len(missing)} package(s). Install with:")
        print(f"  pip install {' '.join(missing)}")
        response = input("\nContinue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Please install missing packages and try again.")
            sys.exit(1)
    
    # Run processing
    run_processing()