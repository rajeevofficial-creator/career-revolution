"""
Document Intelligence System for Career Revolution
Processes career documents and extracts intelligent insights for job profile recommendations.
"""

import os
import json
import hashlib
import re
import statistics
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
from enum import Enum


class DocumentCategory(Enum):
    CV_RESUME = "cv_resume"
    CERTIFICATION = "certification"
    REFERENCE = "reference"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    SALARY = "salary"
    CONTRACT = "contract"
    OTHER = "other"


class DocumentIntelligenceSystem:
    """Main system for processing career documents and extracting intelligent insights."""
    
    def __init__(self, documents_base_path: str = "data", output_path: str = "shared_data"):
        """Initialize the document intelligence system."""
        self.documents_base_path = documents_base_path
        self.output_path = output_path
        
        # Initialize data structures
        self.extracted_data = {
            'skills': set(),
            'experience': [],
            'education': [],
            'certifications': [],
            'documents': {}
        }
        
        # Skills database for categorization
        self.skills_database = {
            'technical': [
                'python', 'java', 'javascript', 'sql', 'html', 'css', 'cloud', 'aws', 'azure',
                'docker', 'kubernetes', 'linux', 'devops', 'ci/cd', 'agile', 'scrum', 'ai', 'ml',
                'data analysis', 'big data', 'cybersecurity', 'networking', 'troubleshooting'
            ],
            'management': [
                'project management', 'team leadership', 'strategic planning', 'budget management',
                'stakeholder management', 'change management', 'risk management', 'process improvement',
                'vendor management', 'resource planning', 'performance management', 'coaching', 'mentoring'
            ],
            'industry_specific': [
                'gmp', 'gxp', 'regulatory compliance', 'clinical trials', 'pharmacovigilance',
                'financial reporting', 'risk assessment', 'investment banking', 'portfolio management',
                'digital transformation', 'it strategy', 'business intelligence', 'erp', 'sap', 'oracle'
            ],
            'soft_skills': [
                'communication', 'presentation', 'negotiation', 'problem solving', 'critical thinking',
                'adaptability', 'collaboration', 'creativity', 'time management', 'attention to detail'
            ]
        }
        
        # Job profiles database
        self.job_profiles = {
            'it_director_pharma': {
                'title': 'IT Director - Pharmaceutical',
                'industry': 'pharma_it',
                'required_experience': 10,
                'education': 'master',
                'required_skills': ['project management', 'strategic planning', 'team leadership', 
                                   'regulatory compliance', 'digital transformation'],
                'certifications': ['PMP', 'ITIL'],
                'description': 'Lead IT strategy and digital transformation in pharmaceutical environment.'
            },
            'digital_transformation_lead': {
                'title': 'Digital Transformation Lead',
                'industry': 'digital_transformation',
                'required_experience': 8,
                'education': 'master',
                'required_skills': ['digital transformation', 'change management', 'strategic planning',
                                   'stakeholder management', 'process improvement'],
                'certifications': ['Agile', 'Scrum'],
                'description': 'Drive digital transformation initiatives across organizations.'
            },
            'it_business_partner': {
                'title': 'IT Business Partner - Finance',
                'industry': 'finance_it',
                'required_experience': 7,
                'education': 'bachelor',
                'required_skills': ['stakeholder management', 'business intelligence', 'financial reporting',
                                   'project management', 'communication'],
                'certifications': ['ITIL', 'PMP'],
                'description': 'Bridge IT and finance departments to deliver business value.'
            },
            'senior_project_manager': {
                'title': 'Senior Project Manager',
                'industry': 'consulting',
                'required_experience': 8,
                'education': 'bachelor',
                'required_skills': ['project management', 'risk management', 'budget management',
                                   'vendor management', 'communication'],
                'certifications': ['PMP', 'Prince2'],
                'description': 'Manage complex projects from initiation to completion.'
            },
            'service_delivery_manager': {
                'title': 'Service Delivery Manager',
                'industry': 'it_services',
                'required_experience': 6,
                'education': 'bachelor',
                'required_skills': ['service delivery', 'client management', 'sla management',
                                   'process improvement', 'team leadership'],
                'certifications': ['ITIL', 'ISO20000'],
                'description': 'Ensure high-quality IT service delivery to clients.'
            }
        }
        
        # Industry sectors
        self.industry_sectors = {
            'pharma_it': {'name': 'Pharmaceutical IT', 'location': 'Basel, Switzerland'},
            'finance_it': {'name': 'Financial Services IT', 'location': 'Zurich, Switzerland'},
            'digital_transformation': {'name': 'Digital Transformation', 'location': 'Global'},
            'consulting': {'name': 'Consulting', 'location': 'Global'},
            'it_services': {'name': 'IT Services', 'location': 'Global'}
        }
        
        # Create output directories
        self._create_output_directories()
    
    def _create_output_directories(self):
        """Create necessary output directories."""
        directories = [
            os.path.join(self.output_path, "profile"),
            os.path.join(self.output_path, "analysis"),
            os.path.join(self.output_path, "documents"),
            os.path.join(self.output_path, "reports")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def scan_documents_directory(self) -> Dict[str, List[str]]:
        """Scan the documents directory and categorize files."""
        categorized_files = {category.value: [] for category in DocumentCategory}
        categorized_files['unknown'] = []
        
        if not os.path.exists(self.documents_base_path):
            print(f"Warning: Documents directory '{self.documents_base_path}' not found.")
            return categorized_files
        
        # Walk through the directory
        for root, dirs, files in os.walk(self.documents_base_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                category = self._categorize_file(filename, file_path)
                categorized_files[category].append(file_path)
        
        # Print summary
        print(f"\nDocument Scanning Summary:")
        for category, files in categorized_files.items():
            if files:
                print(f"  {category}: {len(files)} files")
        
        total_files = sum(len(files) for files in categorized_files.values())
        print(f"\nTotal files found: {total_files}")
        
        return categorized_files
    
    def _categorize_file(self, filename: str, file_path: str) -> str:
        """Categorize a file based on its name and content."""
        filename_lower = filename.lower()
        
        # Check for CV/Resume
        cv_keywords = ['cv', 'resume', 'curriculum vitae', 'lebenslauf']
        if any(keyword in filename_lower for keyword in cv_keywords):
            return DocumentCategory.CV_RESUME.value
        
        # Check for certifications
        cert_keywords = ['certificate', 'certification', 'cert', 'diploma', 'qualification', 'pmp', 'itil']
        if any(keyword in filename_lower for keyword in cert_keywords):
            return DocumentCategory.CERTIFICATION.value
        
        # Check for references
        ref_keywords = ['reference', 'recommendation', 'testimonial', 'endorsement']
        if any(keyword in filename_lower for keyword in ref_keywords):
            return DocumentCategory.REFERENCE.value
        
        # Check for cover letters
        cover_keywords = ['cover letter', 'application letter', 'motivation letter']
        if any(keyword in filename_lower for keyword in cover_keywords):
            return DocumentCategory.COVER_LETTER.value
        
        # Check for portfolio
        portfolio_keywords = ['portfolio', 'work samples', 'projects']
        if any(keyword in filename_lower for keyword in portfolio_keywords):
            return DocumentCategory.PORTFOLIO.value
        
        # Check for salary documents
        salary_keywords = ['salary', 'compensation', 'pay', 'income']
        if any(keyword in filename_lower for keyword in salary_keywords):
            return DocumentCategory.SALARY.value
        
        # Check for contracts
        contract_keywords = ['contract', 'agreement', 'employment']
        if any(keyword in filename_lower for keyword in contract_keywords):
            return DocumentCategory.CONTRACT.value
        
        # Try to extract text from the file for better categorization
        try:
            text = self.extract_text_from_file(file_path)
            if text:
                text_lower = text.lower()
                
                if any(keyword in text_lower for keyword in cv_keywords):
                    return DocumentCategory.CV_RESUME.value
                elif any(keyword in text_lower for keyword in cert_keywords):
                    return DocumentCategory.CERTIFICATION.value
                elif any(keyword in text_lower for keyword in ref_keywords):
                    return DocumentCategory.REFERENCE.value
        except:
            pass
        
        return DocumentCategory.OTHER.value
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file formats."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.pdf':
                return self._extract_text_from_pdf(file_path)
            elif file_ext == '.docx':
                return self._extract_text_from_docx(file_path)
            elif file_ext == '.txt':
                return self._extract_text_from_txt(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                return self._extract_text_from_image(file_path)
            else:
                print(f"Warning: Unsupported file format: {file_ext}")
                return ""
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF files."""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
            return text
        except ImportError:
            print("PyPDF2 not installed. Using fallback method.")
            return f"[PDF content from {os.path.basename(file_path)}]"
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return f"[PDF content from {os.path.basename(file_path)}]"
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX files."""
        try:
            import docx
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except ImportError:
            print("python-docx not installed. Using fallback method.")
            return f"[DOCX content from {os.path.basename(file_path)}]"
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
            return f"[DOCX content from {os.path.basename(file_path)}]"
    
    def _extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                print(f"Error reading TXT {file_path}: {e}")
                return f"[TXT content from {os.path.basename(file_path)}]"
        except Exception as e:
            print(f"Error reading TXT {file_path}: {e}")
            return f"[TXT content from {os.path.basename(file_path)}]"
    
    def _extract_text_from_image(self, file_path: str) -> str:
        """Extract text from image files using OCR."""
        try:
            import pytesseract
            from PIL import Image
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except ImportError:
            print("pytesseract or PIL not installed. Cannot extract text from images.")
            return f"[Image content from {os.path.basename(file_path)}]"
        except Exception as e:
            print(f"Error processing image {file_path}: {e}")
            return f"[Image content from {os.path.basename(file_path)}]"
    
    def analyze_document_content(self, text: str, file_path: str, category: str) -> Dict[str, Any]:
        """Analyze document content and extract structured information."""
        analysis = {
            'file_path': file_path,
            'category': category,
            'skills': [],
            'experience_years': 0,
            'education_level': '',
            'certifications': [],
            'industries': [],
            'key_phrases': [],
            'summary': ''
        }
        
        text_lower = text.lower()
        
        # Extract skills
        analysis['skills'] = self._extract_skills(text)
        
        # Extract experience
        analysis['experience_years'] = self._extract_experience(text)
        
        # Extract education
        analysis['education_level'] = self._extract_education_level(text)
        
        # Extract certifications
        analysis['certifications'] = self._extract_certifications(text)
        
        # Extract industries
        analysis['industries'] = self._extract_industries(text)
        
        # Extract key phrases
        analysis['key_phrases'] = self._extract_key_phrases(text)
        
        # Generate summary
        analysis['summary'] = self._generate_document_summary(analysis, category)
        
        return analysis
    
    def _extract_skills(self, text: str) -> List[Dict[str, str]]:
        """Extract skills from text."""
        skills = []
        text_lower = text.lower()
        
        # Check for skills from database
        for skill_type, skill_list in self.skills_database.items():
            for skill in skill_list:
                if skill.lower() in text_lower:
                    # Find context (surrounding words)
                    context_start = max(0, text_lower.find(skill.lower()) - 50)
                    context_end = min(len(text_lower), text_lower.find(skill.lower()) + len(skill) + 50)
                    context = text[context_start:context_end].strip()
                    
                    skills.append({
                        'skill': skill,
                        'type': skill_type,
                        'context': context
                    })
        
        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in skills:
            skill_key = skill['skill'].lower()
            if skill_key not in seen:
                seen.add(skill_key)
                unique_skills.append(skill)
        
        return unique_skills
    
    def _extract_experience(self, text: str) -> int:
        """Extract years of experience from text."""
        # Look for patterns like "X years of experience", "X+ years", "X yoe"
        patterns = [
            r'(\d+)\s*\+?\s*years?\s*(?:of\s*)?experience',
            r'experience\s*:\s*(\d+)\s*years?',
            r'(\d+)\s*yoe',
            r'(\d+)\s*years?\s*in\s*[a-zA-Z\s]+'
        ]
        
        max_years = 0
        text_lower = text.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                try:
                    years = int(match)
                    max_years = max(max_years, years)
                except ValueError:
                    pass
        
        # If no pattern found, try to extract from dates
        if max_years == 0:
            # Look for date ranges like "2015-2020" or "Jan 2018 - Present"
            date_patterns = [
                r'\b(19|20)\d{2}\s*[-–]\s*(?:present|now|(19|20)\d{2})\b',
                r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\s*[-–]\s*(?:present|now|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})\b'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    # Rough estimate: each date range is at least 1 year
                    max_years = len(matches)
        
        return min(max_years, 40)  # Cap at 40 years
    
    def _extract_education_level(self, text: str) -> str:
        """Extract highest education level from text."""
        text_lower = text.lower()
        
        education_levels = [
            ('phd', ['phd', 'doctorate', 'ph.d', 'd.phil']),
            ('master', ['master', 'msc', 'ms', 'mba', 'meng', 'ma']),
            ('bachelor', ['bachelor', 'bsc', 'bs', 'ba', 'beng']),
            ('diploma', ['diploma', 'certificate', 'associate'])
        ]
        
        for level, keywords in education_levels:
            for keyword in keywords:
                if keyword in text_lower:
                    return level
        
        return ''
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications from text."""
        certifications = []
        text_lower = text.lower()
        
        # Common certifications
        common_certs = [
            'pmp', 'itil', 'prince2', 'scrum', 'agile', 'six sigma', 'cisp', 'cisa',
            'aws certified', 'azure certified', 'google cloud', 'oracle certified',
            'sap certified', 'project management professional', 'certified information systems'
        ]
        
        for cert in common_certs:
            if cert in text_lower:
                # Capitalize appropriately
                cert_display = cert.title() if len(cert.split()) == 1 else ' '.join([word.capitalize() for word in cert.split()])
                certifications.append(cert_display)
        
        # Look for "certified in" or "certification in" patterns
        cert_patterns = [
            r'certified\s+in\s+([A-Za-z\s]+)',
            r'certification\s+in\s+([A-Za-z\s]+)',
            r'([A-Za-z\s]+)\s+certification',
            r'([A-Za-z\s]+)\s+certificate'
        ]
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                cert_name = match.strip().title()
                if cert_name and len(cert_name) > 3:
                    certifications.append(cert_name)
        
        return list(set(certifications))  # Remove duplicates
    
    def _extract_industries(self, text: str) -> List[str]:
        """Extract industries mentioned in text."""
        industries = []
        text_lower = text.lower()
        
        # Map keywords to industry codes
        industry_map = {
            'pharma_it': ['pharmaceutical', 'pharma', 'biotech', 'clinical', 'gmp', 'gxp', 'regulatory'],
            'finance_it': ['financial', 'banking', 'insurance', 'investment', 'wealth', 'asset management'],
            'digital_transformation': ['digital transformation', 'digitalization', 'digitization', 'innovation'],
            'consulting': ['consulting', 'advisory', 'strategy', 'management consulting'],
            'it_services': ['it services', 'managed services', 'outsourcing', 'service delivery']
        }
        
        for industry_code, keywords in industry_map.items():
            for keyword in keywords:
                if keyword in text_lower:
                    industries.append(industry_code)
                    break
        
        return list(set(industries))
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text."""
        # Simple implementation: extract sentences with action verbs
        action_verbs = ['led', 'managed', 'developed', 'created', 'implemented', 'improved',
                       'increased', 'reduced', 'optimized', 'designed', 'built', 'established']
        
        sentences = re.split(r'[.!?]+', text)
        key_phrases = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(verb in sentence_lower for verb in action_verbs) and len(sentence_lower) > 20:
                # Clean up the sentence
                clean_sentence = ' '.join(sentence.split())
                if len(clean_sentence) > 10:
                    key_phrases.append(clean_sentence[:200])  # Limit length
        
        return key_phrases[:10]  # Return top 10
    
    def _generate_document_summary(self, analysis: Dict[str, Any], category: str) -> str:
        """Generate a summary for the document."""
        summary_parts = []
        
        if analysis['skills']:
            top_skills = [skill['skill'] for skill in analysis['skills'][:3]]
            summary_parts.append(f"Key skills: {', '.join(top_skills)}")
        
        if analysis['experience_years'] > 0:
            summary_parts.append(f"{analysis['experience_years']} years of experience")
        
        if analysis['education_level']:
            summary_parts.append(f"{analysis['education_level'].title()} level education")
        
        if analysis['certifications']:
            summary_parts.append(f"Certifications: {', '.join(analysis['certifications'][:2])}")
        
        if summary_parts:
            return f"{category.replace('_', ' ').title()}: " + "; ".join(summary_parts)
        else:
            return f"{category.replace('_', ' ').title()} document"
    
    def process_all_documents(self, categorized_files: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """Process all documents and generate comprehensive profile."""
        if categorized_files is None:
            categorized_files = self.scan_documents_directory()
        
        all_analyses = []
        processed_count = 0
        
        print("\nProcessing documents...")
        print("-" * 40)
        
        for category, files in categorized_files.items():
            if category == 'unknown' or not files:
                continue
            
            print(f"\nProcessing {category} documents ({len(files)} files):")
            
            for i, file_path in enumerate(files, 1):
                print(f"  [{i}/{len(files)}] {os.path.basename(file_path)}")
                
                # Extract text
                text = self.extract_text_from_file(file_path)
                if not text or len(text.strip()) < 50:
                    print(f"    Warning: Insufficient text extracted")
                    continue
                
                # Analyze content
                analysis = self.analyze_document_content(text, file_path, category)
                all_analyses.append(analysis)
                processed_count += 1
                
                # Update master data structures
                self._update_master_data(analysis)
        
        print(f"\nProcessed {processed_count} documents successfully")
        
        # Generate comprehensive profile
        profile = self._generate_comprehensive_profile()
        
        # Recommend job profiles
        recommendations = self._recommend_job_profiles(profile)
        
        # Save results
        self._save_results(profile, recommendations)
        
        return {
            'profile': profile,
            'recommendations': recommendations,
            'analyses': all_analyses
        }
    
    def _update_master_data(self, analysis: Dict[str, Any]):
        """Update master data structures with analysis results."""
        # Add skills
        for skill_info in analysis['skills']:
            self.extracted_data['skills'].add(skill_info['skill'])
        
        # Add experience
        if analysis['experience_years'] > 0:
            self.extracted_data['experience'].append(analysis['experience_years'])
        
        # Add education
        if analysis['education_level']:
            self.extracted_data['education'].append(analysis['education_level'])
        
        # Add certifications
        self.extracted_data['certifications'].extend(analysis['certifications'])
        
        # Store document analysis
        doc_id = hashlib.md5(analysis['file_path'].encode()).hexdigest()[:8]
        self.extracted_data['documents'][doc_id] = analysis
    
    def _generate_comprehensive_profile(self) -> Dict[str, Any]:
        """Generate a comprehensive profile from all extracted data."""
        profile = {
            'summary': {},
            'skills': {},
            'experience': {},
            'education': {},
            'certifications': {},
            'industries': {}
        }
        
        # Skills analysis
        skill_counts = defaultdict(int)
        skill_types = defaultdict(list)
        
        for skill in self.extracted_data['skills']:
            # Find skill type
            skill_type = 'other'
            for type_name, skills_list in self.skills_database.items():
                if skill.lower() in [s.lower() for s in skills_list]:
                    skill_type = type_name
                    break
            
            skill_counts[skill_type] += 1
            skill_types[skill_type].append(skill)
        
        profile['skills'] = {
            'total_count': len(self.extracted_data['skills']),
            'by_type': dict(skill_counts),
            'detailed': dict(skill_types)
        }
        
        # Experience analysis
        if self.extracted_data['experience']:
            profile['experience'] = {
                'max_years': max(self.extracted_data['experience']),
                'avg_years': statistics.mean(self.extracted_data['experience']),
                'min_years': min(self.extracted_data['experience']),
                'all_values': self.extracted_data['experience']
            }
        else:
            profile['experience'] = {'max_years': 0, 'avg_years': 0, 'min_years': 0}
        
        # Education analysis
        education_levels = {
            'phd': 4,
            'master': 3,
            'bachelor': 2,
            'diploma': 1,
            '': 0
        }
        
        if self.extracted_data['education']:
            highest_level = max(
                self.extracted_data['education'],
                key=lambda x: education_levels.get(x, 0)
            )
            profile['education'] = {
                'highest_level': highest_level,
                'all_levels': list(set(self.extracted_data['education'])),
                'count': len(self.extracted_data['education'])
            }
        else:
            profile['education'] = {'highest_level': 'unknown', 'all_levels': []}
        
        # Certifications analysis
        cert_counts = defaultdict(int)
        for cert in self.extracted_data['certifications']:
            cert_counts[cert] += 1
        
        profile['certifications'] = {
            'total_count': len(self.extracted_data['certifications']),
            'unique_count': len(set(self.extracted_data['certifications'])),
            'by_type': dict(cert_counts)
        }
        
        # Industry exposure
        industry_exposure = defaultdict(int)
        for doc_id, analysis in self.extracted_data['documents'].items():
            for industry in analysis.get('industries', []):
                industry_exposure[industry] += 1
        
        profile['industries'] = {
            'exposure': dict(industry_exposure),
            'primary': max(industry_exposure.items(), key=lambda x: x[1])[0] if industry_exposure else 'unknown'
        }
        
        # Summary
        profile['summary'] = {
            'total_documents_analyzed': len(self.extracted_data['documents']),
            'total_skills_identified': len(self.extracted_data['skills']),
            'years_experience': profile['experience']['max_years'],
            'highest_education': profile['education']['highest_level'],
            'certification_count': profile['certifications']['total_count'],
            'primary_industry': profile['industries']['primary'],
            'analysis_date': datetime.now().isoformat()
        }
        
        return profile
    
    def _recommend_job_profiles(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend job profiles based on extracted profile data."""
        recommendations = []
        
        for profile_id, job_profile in self.job_profiles.items():
            score, gaps = self._calculate_profile_fit(profile, job_profile)
            
            recommendations.append({
                'profile_id': profile_id,
                'title': job_profile['title'],
                'industry': self.industry_sectors[job_profile['industry']]['name'],
                'fit_score': score,
                'skill_gaps': gaps,
                'match_details': self._get_match_details(profile, job_profile)
            })
        
        # Sort by fit score (descending)
        recommendations.sort(key=lambda x: x['fit_score'], reverse=True)
        
        return recommendations[:7]  # Return top 7 recommendations
    
    def _calculate_profile_fit(self, profile: Dict[str, Any], job_profile: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Calculate fit score between user profile and job profile."""
        total_score = 0
        max_score = 0
        gaps = []
        
        # Experience match (30% weight)
        user_exp = profile['experience']['max_years']
        req_exp = job_profile['required_experience']
        
        if user_exp >= req_exp:
            exp_score = 30
        else:
            exp_score = max(0, 30 * (user_exp / req_exp))
            gaps.append(f"Experience: {user_exp}y vs required {req_exp}y")
        
        total_score += exp_score
        max_score += 30
        
        # Skills match (40% weight)
        user_skills = [s.lower() for s in profile['skills']['detailed'].get('technical', []) + 
                      profile['skills']['detailed'].get('management', []) + 
                      profile['skills']['detailed'].get('industry_specific', [])]
        
        required_skills = [s.lower() for s in job_profile['required_skills']]
        matched_skills = [skill for skill in required_skills if any(user_skill for user_skill in user_skills if skill in user_skill)]
        
        skill_score = 40 * (len(matched_skills) / len(required_skills))
        total_score += skill_score
        max_score += 40
        
        missing_skills = [skill for skill in required_skills if not any(user_skill for user_skill in user_skills if skill in user_skill)]
        if missing_skills:
            gaps.append(f"Missing skills: {', '.join(missing_skills[:3])}")
        
        # Education match (15% weight)
        education_levels = {'phd': 4, 'master': 3, 'bachelor': 2, 'diploma': 1}
        user_edu = education_levels.get(profile['education']['highest_level'], 0)
        req_edu = education_levels.get(job_profile['education'], 0)
        
        if user_edu >= req_edu:
            edu_score = 15
        else:
            edu_score = max(0, 15 * (user_edu / max(req_edu, 1)))
            gaps.append(f"Education: {profile['education']['highest_level']} vs required {job_profile['education']}")
        
        total_score += edu_score
        max_score += 15
        
        # Certifications match (15% weight)
        user_certs = [c.lower() for c in profile['certifications']['by_type'].keys()]
        req_certs = [c.lower() for c in job_profile.get('certifications', [])]
        
        if req_certs:
            matched_certs = [cert for cert in req_certs if any(user_cert for user_cert in user_certs if cert in user_cert)]
            cert_score = 15 * (len(matched_certs) / len(req_certs))
            
            missing_certs = [cert for cert in req_certs if not any(user_cert for user_cert in user_certs if cert in user_cert)]
            if missing_certs:
                gaps.append(f"Missing certifications: {', '.join(missing_certs)}")
        else:
            cert_score = 15  # No certifications required
        
        total_score += cert_score
        max_score += 15
        
        # Calculate final percentage
        final_score = (total_score / max_score) * 100 if max_score > 0 else 0
        
        return round(final_score, 1), gaps
    
    def _get_match_details(self, profile: Dict[str, Any], job_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed match information."""
        user_skills = [s.lower() for s in profile['skills']['detailed'].get('technical', []) + 
                      profile['skills']['detailed'].get('management', []) + 
                      profile['skills']['detailed'].get('industry_specific', [])]
        
        required_skills = [s.lower() for s in job_profile['required_skills']]
        matched_skills = [skill for skill in required_skills if any(user_skill for user_skill in user_skills if skill in user_skill)]
        
        return {
            'experience_match': f"{profile['experience']['max_years']}y vs {job_profile['required_experience']}y required",
            'skills_match': f"{len(matched_skills)}/{len(required_skills)} skills matched",
            'education_match': f"{profile['education']['highest_level']} vs {job_profile['education']} required",
            'industry_alignment': job_profile['industry']
        }
    
    def _save_results(self, profile: Dict[str, Any], recommendations: List[Dict[str, Any]]):
        """Save analysis results to files."""
        # Save profile data
        profile_path = os.path.join(self.output_path, "profile", "master_profile.json")
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        
        # Save recommendations
        recommendations_path = os.path.join(self.output_path, "analysis", "job_recommendations.json")
        with open(recommendations_path, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, indent=2, ensure_ascii=False)
        
        # Save skill gap analysis
        gap_analysis = []
        for rec in recommendations:
            if rec['skill_gaps']:
                gap_analysis.append({
                    'job_title': rec['title'],
                    'fit_score': rec['fit_score'],
                    'gaps': rec['skill_gaps']
                })
        
        gaps_path = os.path.join(self.output_path, "analysis", "skill_gaps.json")
        with open(gaps_path, 'w', encoding='utf-8') as f:
            json.dump(gap_analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to:")
        print(f"  Profile: {profile_path}")
        print(f"  Recommendations: {recommendations_path}")
        print(f"  Skill Gaps: {gaps_path}")
    
    def generate_report(self) -> str:
        """Generate a human-readable report of the analysis."""
        # Load saved data
        profile_path = os.path.join(self.output_path, "profile", "master_profile.json")
        recommendations_path = os.path.join(self.output_path, "analysis", "job_recommendations.json")
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            
            with open(recommendations_path, 'r', encoding='utf-8') as f:
                recommendations = json.load(f)
        except FileNotFoundError:
            return "No analysis data found. Please run process_all_documents() first."
        
        # Generate report
        report = []
        report.append("=" * 80)
        report.append("CAREER REVOLUTION - DOCUMENT INTELLIGENCE REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append("PROFILE SUMMARY")
        report.append("-" * 40)
        summary = profile['summary']
        report.append(f"• Documents Analyzed: {summary['total_documents_analyzed']}")
        report.append(f"• Skills Identified: {summary['total_skills_identified']}")
        report.append(f"• Years of Experience: {summary['years_experience']}")
        report.append(f"• Highest Education: {summary['highest_education'].upper()}")
        report.append(f"• Certifications: {summary['certification_count']}")
        report.append(f"• Primary Industry: {summary['primary_industry'].replace('_', ' ').title()}")
        report.append("")
        
        # Top Skills
        report.append("TOP SKILLS BY CATEGORY")
        report.append("-" * 40)
        for skill_type, skills in profile['skills']['detailed'].items():
            if skills:
                report.append(f"  {skill_type.title()}:")
                for skill in skills[:5]:  # Top 5 per category
                    report.append(f"    • {skill}")
        report.append("")
        
        # Job Recommendations
        report.append("TOP JOB PROFILE RECOMMENDATIONS")
        report.append("-" * 40)
        for i, rec in enumerate(recommendations[:5], 1):
            report.append(f"{i}. {rec['title']}")
            report.append(f"   Industry: {rec['industry']}")
            report.append(f"   Fit Score: {rec['fit_score']}%")
            report.append(f"   Match: {rec['match_details']['skills_match']}")
            
            if rec['skill_gaps']:
                report.append(f"   Areas for Improvement:")
                for gap in rec['skill_gaps'][:2]:  # Top 2 gaps
                    report.append(f"     • {gap}")
            report.append("")
        
        # Actionable Insights
        report.append("ACTIONABLE INSIGHTS")
        report.append("-" * 40)
        
        # Identify top 3 skill gaps across all recommendations
        all_gaps = []
        for rec in recommendations[:5]:
            all_gaps.extend(rec['skill_gaps'])
        
        if all_gaps:
            # Count frequency of gap types
            gap_counts = defaultdict(int)
            for gap in all_gaps:
                if "Missing skills:" in gap:
                    gap_counts['skills'] += 1
                elif "Experience:" in gap:
                    gap_counts['experience'] += 1
                elif "Education:" in gap:
                    gap_counts['education'] += 1
                elif "Missing certifications:" in gap:
                    gap_counts['certifications'] += 1
            
            if gap_counts:
                report.append("Priority Areas to Address:")
                for gap_type, count in sorted(gap_counts.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  • {gap_type.title()}: Appears in {count} recommended profiles")
        
        report.append("")
        report.append("=" * 80)
        report.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main function to run the document intelligence system."""
    print("Career Revolution - Document Intelligence System")
    print("=" * 60)
    
    # Initialize system
    system = DocumentIntelligenceSystem(
        documents_base_path="data",
        output_path="shared_data"
    )
    
    # Scan documents
    print("\n1. Scanning documents directory...")
    categorized_files = system.scan_documents_directory()
    
    # Process documents
    print("\n2. Processing documents and extracting information...")
    results = system.process_all_documents(categorized_files)
    
    # Generate report
    print("\n3. Generating analysis report...")
    report = system.generate_report()
    
    print("\n" + report)
    
    # Save report to file
    report_path = os.path.join("shared_data", "analysis", "intelligence_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    print("\nDocument Intelligence System completed successfully!")


if __name__ == "__main__":
    main()