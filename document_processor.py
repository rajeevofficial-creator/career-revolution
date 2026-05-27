"""
AI Document Processor for Career Revolution
Extracts structured data from career documents and builds repository.
"""

import os
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import PyPDF2
from docx import Document as DocxDocument
import pytesseract
from PIL import Image
import io

class DocumentProcessor:
    """Process career documents and extract structured information."""
    
    def __init__(self, upload_base_path: str = "uploads"):
        self.upload_base_path = upload_base_path
        self.repository_base = "repository"
        
        # Create repository structure
        os.makedirs(self.repository_base, exist_ok=True)
        
        # Supported file extensions
        self.supported_extensions = {
            '.pdf': self._extract_pdf,
            '.docx': self._extract_docx,
            '.doc': self._extract_doc,  # Will need conversion
            '.txt': self._extract_txt,
            '.png': self._extract_image,
            '.jpg': self._extract_image,
            '.jpeg': self._extract_image
        }
        
        # Document classification patterns
        self.classification_patterns = {
            'cv_resume': {
                'keywords': ['cv', 'resume', 'curriculum vitae', 'lebenslauf', 'cv-'],
                'sections': ['experience', 'education', 'skills', 'summary', 'objective']
            },
            'certification': {
                'keywords': ['certificate', 'certification', 'diploma', 'degree', 'license'],
                'patterns': ['awarded to', 'successfully completed', 'passed', 'qualified']
            },
            'reference': {
                'keywords': ['reference', 'recommendation', 'testimonial', 'letter'],
                'patterns': ['to whom it may concern', 'recommends', 'worked with', 'reference for']
            },
            'cover_letter': {
                'keywords': ['cover letter', 'application letter', 'motivation'],
                'patterns': ['dear', 'application for', 'interested in', 'sincerely']
            }
        }
        
        # Extraction patterns
        self.extraction_patterns = {
            'name': r'(?i)(?:name|full name)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            'email': r'[\w\.-]+@[\w\.-]+\.\w+',
            'phone': r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            'linkedin': r'(?:linkedin\.com/in/|linkedin\.com/company/)[\w\-]+',
            'date_range': r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\s*(?:-|to)\s*(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|\bPresent\b)',
            'skills': r'(?i)(?:skills|competencies|expertise)[:\s]*(.*?)(?:\n\n|\n\s*\n|$)',
            'education': r'(?i)(?:education|qualifications)[:\s]*(.*?)(?:\n\n|\n\s*\n|$)',
            'experience': r'(?i)(?:experience|work history|employment)[:\s]*(.*?)(?:\n\n|\n\s*\n|$)'
        }
    
    def process_user_documents(self, user_id: int) -> Dict[str, Any]:
        """Process all documents for a user and build repository."""
        print(f"\n{'='*60}")
        print(f"PROCESSING DOCUMENTS FOR USER {user_id}")
        print(f"{'='*60}")
        
        user_repo_path = os.path.join(self.repository_base, f"user_{user_id}")
        os.makedirs(user_repo_path, exist_ok=True)
        
        # Create repository structure
        repo_structure = {
            'documents': os.path.join(user_repo_path, 'documents'),
            'extracted': os.path.join(user_repo_path, 'extracted'),
            'analysis': os.path.join(user_repo_path, 'analysis')
        }
        
        for folder in repo_structure.values():
            os.makedirs(folder, exist_ok=True)
        
        # Find user's documents
        user_upload_path = os.path.join(self.upload_base_path, str(user_id))
        if not os.path.exists(user_upload_path):
            print(f"No documents found for user {user_id}")
            return {'status': 'error', 'message': 'No documents found'}
        
        # Process each document
        processed_docs = []
        issues = []
        
        for root, dirs, files in os.walk(user_upload_path):
            for file in files:
                file_path = os.path.join(root, file)
                print(f"\nProcessing: {file}")
                
                result = self.process_single_document(file_path, user_id)
                
                if result['status'] == 'success':
                    processed_docs.append(result)
                    print(f"  ✓ {result['document_type']} - {len(result.get('extracted_text', ''))} chars")
                else:
                    issues.append({
                        'file': file,
                        'error': result.get('error', 'Unknown error'),
                        'suggestion': result.get('suggestion', '')
                    })
                    print(f"  ✗ {result.get('error', 'Failed')}")
        
        # Build consolidated profile
        if processed_docs:
            consolidated_profile = self._build_consolidated_profile(processed_docs, user_id)
            
            # Save repository
            self._save_repository(consolidated_profile, user_repo_path)
            
            # Generate analysis
            analysis = self._generate_analysis(consolidated_profile)
            
            return {
                'status': 'success',
                'processed_count': len(processed_docs),
                'issue_count': len(issues),
                'profile': consolidated_profile,
                'analysis': analysis,
                'issues': issues,
                'repository_path': user_repo_path
            }
        else:
            return {
                'status': 'error',
                'message': 'No documents could be processed',
                'issues': issues
            }
    
    def process_single_document(self, file_path: str, user_id: int) -> Dict[str, Any]:
        """Process a single document and extract information."""
        try:
            # Get file extension
            ext = os.path.splitext(file_path)[1].lower()
            
            # Check if supported
            if ext not in self.supported_extensions:
                return {
                    'status': 'error',
                    'error': f'Unsupported file format: {ext}',
                    'suggestion': 'Convert to PDF, DOCX, or TXT format'
                }
            
            # Extract text
            extractor = self.supported_extensions[ext]
            extracted_text = extractor(file_path)
            
            if not extracted_text or len(extracted_text.strip()) < 10:
                return {
                    'status': 'error',
                    'error': 'No text could be extracted',
                    'suggestion': 'File may be corrupted or image quality is poor'
                }
            
            # Classify document
            document_type = self._classify_document(extracted_text, os.path.basename(file_path))
            
            # Extract structured data
            structured_data = self._extract_structured_data(extracted_text, document_type)
            
            # Calculate hash for duplicate detection
            content_hash = hashlib.md5(extracted_text.encode()).hexdigest()
            
            return {
                'status': 'success',
                'file_path': file_path,
                'filename': os.path.basename(file_path),
                'file_extension': ext,
                'document_type': document_type,
                'extracted_text': extracted_text,
                'structured_data': structured_data,
                'content_hash': content_hash,
                'processing_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'suggestion': 'Try uploading a different version of the file'
            }
    
    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"  PDF extraction error: {e}")
        return text
    
    def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        text = ""
        try:
            doc = DocxDocument(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"  DOCX extraction error: {e}")
        return text
    
    def _extract_doc(self, file_path: str) -> str:
        """Extract text from DOC file (requires conversion)."""
        # For now, return empty - would need antiword or other converter
        return "DOC format requires conversion to DOCX or PDF"
    
    def _extract_txt(self, file_path: str) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                print(f"  TXT extraction error: {e}")
                return ""
    
    def _extract_image(self, file_path: str) -> str:
        """Extract text from image using OCR."""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            print(f"  Image OCR error: {e}")
            return ""
    
    def _classify_document(self, text: str, filename: str) -> str:
        """Classify document type based on content and filename."""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        scores = {}
        
        for doc_type, patterns in self.classification_patterns.items():
            score = 0
            
            # Check filename keywords
            for keyword in patterns['keywords']:
                if keyword in filename_lower:
                    score += 3
            
            # Check content keywords
            for keyword in patterns['keywords']:
                if keyword in text_lower:
                    score += 2
            
            # Check content patterns
            if 'patterns' in patterns:
                for pattern in patterns['patterns']:
                    if pattern in text_lower:
                        score += 1
            
            # Check sections (for CVs)
            if doc_type == 'cv_resume' and 'sections' in patterns:
                for section in patterns['sections']:
                    if section in text_lower:
                        score += 1
            
            scores[doc_type] = score
        
        # Get highest scoring type
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return 'other'
    
    def _extract_structured_data(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Extract structured data from text based on document type."""
        structured_data = {
            'metadata': {},
            'entities': {},
            'sections': {}
        }
        
        # Extract basic metadata
        for field, pattern in self.extraction_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                structured_data['metadata'][field] = matches[0] if isinstance(matches[0], str) else matches
        
        # Type-specific extraction
        if doc_type == 'cv_resume':
            structured_data.update(self._extract_cv_data(text))
        elif doc_type == 'certification':
            structured_data.update(self._extract_certification_data(text))
        elif doc_type == 'reference':
            structured_data.update(self._extract_reference_data(text))
        elif doc_type == 'cover_letter':
            structured_data.update(self._extract_cover_letter_data(text))
        
        return structured_data
    
    def _extract_cv_data(self, text: str) -> Dict[str, Any]:
        """Extract CV-specific data."""
        cv_data = {
            'sections': {},
            'skills': [],
            'experiences': [],
            'education': [],
            'certifications': []
        }
        
        # Try to identify sections
        section_headers = [
            'experience', 'work history', 'employment',
            'education', 'qualifications', 'academic',
            'skills', 'competencies', 'expertise',
            'certifications', 'certificates', 'licenses',
            'projects', 'achievements', 'publications',
            'languages', 'interests', 'hobbies'
        ]
        
        lines = text.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            line_lower = line.strip().lower()
            
            # Check if this line starts a new section
            is_section_header = False
            for header in section_headers:
                if line_lower.startswith(header) or header in line_lower:
                    # Save previous section
                    if current_section and section_content:
                        cv_data['sections'][current_section] = '\n'.join(section_content)
                    
                    # Start new section
                    current_section = header
                    section_content = []
                    is_section_header = True
                    break
            
            if not is_section_header and current_section:
                section_content.append(line.strip())
        
        # Save last section
        if current_section and section_content:
            cv_data['sections'][current_section] = '\n'.join(section_content)
        
        # Extract skills (simple pattern matching)
        skill_keywords = [
            'project management', 'it governance', 'servicenow', 'sap',
            'azure', 'agile', 'scrum', 'stakeholder management', 'leadership',
            'python', 'sql', 'data analysis', 'business intelligence'
        ]
        
        for skill in skill_keywords:
            if skill in text.lower():
                cv_data['skills'].append(skill.title())
        
        return cv_data
    
    def _extract_certification_data(self, text: str) -> Dict[str, Any]:
        """Extract certification data."""
        cert_data = {
            'certification_name': '',
            'issuing_organization': '',
            'issue_date': '',
            'expiry_date': '',
            'credential_id': ''
        }
        
        # Simple pattern matching for common certifications
        cert_patterns = {
            'pmp': r'(?:PMP|Project Management Professional)[\s\S]*?(?:certified|awarded)[\s\S]*?(\d{4})',
            'itil': r'(?:ITIL)[\s\S]*?(?:Foundation|certified)[\s\S]*?(\d{4})',
            'cgeit': r'(?:CGEIT)[\s\S]*?(\d{4})',
            'german': r'(?:German|Deutsch)[\s\S]*?(?:B1|B2|C1)[\s\S]*?(\d{4})'
        }
        
        for cert, pattern in cert_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cert_data['certification_name'] = cert.upper()
                cert_data['issue_date'] = match.group(1)
                break
        
        return cert_data
    
    def _extract_reference_data(self, text: str) -> Dict[str, Any]:
        """Extract reference letter data."""
        ref_data = {
            'referrer_name': '',
            'referrer_position': '',
            'referrer_company': '',
            'reference_date': '',
            'relationship': ''
        }
        
        # Try to extract names (simple pattern)
        name_match = re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', text)
        if name_match:
            ref_data['referrer_name'] = name_match.group(0)
        
        # Look for company names
        company_keywords = ['Infosys', 'Dufry', 'Consulting', 'AG', 'GmbH']
        for keyword in company_keywords:
            if keyword in text:
                ref_data['referrer_company'] = keyword
                break
        
        return ref_data
    
    def _extract_cover_letter_data(self, text: str) -> Dict[str, Any]:
        """Extract cover letter data."""
        letter_data = {
            'company': '',
            'position': '',
            'date': '',
            'salutation': '',
            'key_skills_mentioned': []
        }
        
        # Look for company names
        companies = ['UBS', 'Novartis', 'Bayer', 'Roche', 'Swiss Re', 'AXA', 'Credit Suisse']
        for company in companies:
            if company in text:
                letter_data['company'] = company
                break
        
        # Look for position titles
        positions = ['Project Manager', 'Service Manager', 'IT Director', 'Consultant']
        for position in positions:
            if position in text:
                letter_data['position'] = position
                break
        
        return letter_data
    
    def _build_consolidated_profile(self, processed_docs: List[Dict], user_id: int) -> Dict[str, Any]:
        """Build consolidated profile from all processed documents."""
        print(f"\nBuilding consolidated profile from {len(processed_docs)} documents...")
        
        profile = {
            'user_id': user_id,
            'generated_date': datetime.now().isoformat(),
            'document_count': len(processed_docs),
