            'documents_by_type': {},
            'consolidated_data': {
                'personal_info': {},
                'skills': [],
                'experiences': [],
                'education': [],
                'certifications': [],
                'projects': [],
                'languages': [],
                'references': []
            },
            'source_documents': []
        }
        
        # Group documents by type
        for doc in processed_docs:
            doc_type = doc['document_type']
            if doc_type not in profile['documents_by_type']:
                profile['documents_by_type'][doc_type] = []
            
            profile['documents_by_type'][doc_type].append({
                'filename': doc['filename'],
                'content_hash': doc['content_hash'],
                'structured_data': doc['structured_data']
            })
            
            profile['source_documents'].append({
                'filename': doc['filename'],
                'type': doc_type,
                'processing_date': doc['processing_date']
            })
        
        # Consolidate data from all documents
        self._consolidate_profile_data(profile, processed_docs)
        
        # Remove duplicates
        self._deduplicate_profile_data(profile)
        
        print(f"  ✓ Consolidated {len(profile['consolidated_data']['skills'])} skills")
        print(f"  ✓ Found {len(profile['consolidated_data']['experiences'])} experiences")
        print(f"  ✓ Found {len(profile['consolidated_data']['certifications'])} certifications")
        
        return profile
    
    def _consolidate_profile_data(self, profile: Dict, processed_docs: List[Dict]):
        """Consolidate data from all documents into profile."""
        all_skills = set()
        all_certifications = set()
        all_experiences = []
        
        for doc in processed_docs:
            structured_data = doc['structured_data']
            
            # Consolidate skills
            if 'skills' in structured_data:
                for skill in structured_data['skills']:
                    if skill and skill not in ['', ' ']:
                        all_skills.add(skill.title())
            
            # Consolidate certifications
            if 'certification_name' in structured_data.get('metadata', {}):
                cert_name = structured_data['metadata']['certification_name']
                if cert_name:
                    all_certifications.add(cert_name)
            
            # Extract experiences from CV sections
            if doc['document_type'] == 'cv_resume' and 'sections' in structured_data:
                for section_name, section_content in structured_data['sections'].items():
                    if 'experience' in section_name.lower():
                        # Simple experience extraction
                        experiences = self._extract_experiences_from_text(section_content)
                        all_experiences.extend(experiences)
        
        # Update profile
        profile['consolidated_data']['skills'] = list(all_skills)
        profile['consolidated_data']['certifications'] = list(all_certifications)
        profile['consolidated_data']['experiences'] = all_experiences
        
        # Extract personal info from first CV
        for doc in processed_docs:
            if doc['document_type'] == 'cv_resume':
                metadata = doc['structured_data'].get('metadata', {})
                for key in ['name', 'email', 'phone', 'linkedin']:
                    if key in metadata and metadata[key]:
                        profile['consolidated_data']['personal_info'][key] = metadata[key]
                break
    
    def _extract_experiences_from_text(self, text: str) -> List[Dict]:
        """Extract work experiences from text."""
        experiences = []
        
        # Simple pattern for experience entries
        # Looks for: Company - Role (Date Range)
        patterns = [
            r'([A-Z][A-Za-z\s&]+?)\s*[-–]\s*([^(\n]+?)\s*\(([^)]+)\)',
            r'([A-Z][A-Za-z\s&]+?)\s*,\s*([^,\n]+?)\s*,\s*([^,\n]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) >= 3:
                    experiences.append({
                        'company': match[0].strip(),
                        'role': match[1].strip(),
                        'duration': match[2].strip()
                    })
        
        return experiences
    
    def _deduplicate_profile_data(self, profile: Dict):
        """Remove duplicates from consolidated data."""
        consolidated = profile['consolidated_data']
        
        # Deduplicate skills (case insensitive)
        unique_skills = []
        seen_skills = set()
        for skill in consolidated['skills']:
            skill_lower = skill.lower()
            if skill_lower not in seen_skills:
                seen_skills.add(skill_lower)
                unique_skills.append(skill)
        consolidated['skills'] = unique_skills
        
        # Deduplicate certifications
        unique_certs = []
        seen_certs = set()
        for cert in consolidated['certifications']:
            cert_lower = cert.lower()
            if cert_lower not in seen_certs:
                seen_certs.add(cert_lower)
                unique_certs.append(cert)
        consolidated['certifications'] = unique_certs
        
        # Deduplicate experiences (by company and role)
        unique_experiences = []
        seen_experiences = set()
        for exp in consolidated['experiences']:
            key = f"{exp.get('company', '').lower()}|{exp.get('role', '').lower()}"
            if key not in seen_experiences:
                seen_experiences.add(key)
                unique_experiences.append(exp)
        consolidated['experiences'] = unique_experiences
    
    def _save_repository(self, profile: Dict, repo_path: str):
        """Save repository to filesystem."""
        print(f"\nSaving repository to: {repo_path}")
        
        # Save profile
        profile_file = os.path.join(repo_path, 'profile.json')
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Profile saved: {profile_file}")
        
        # Save extracted data by category
        extracted_dir = os.path.join(repo_path, 'extracted')
        
        categories = ['skills', 'certifications', 'experiences', 'personal_info']
        for category in categories:
            if category in profile['consolidated_data']:
                data = profile['consolidated_data'][category]
                if data:  # Only save if there's data
                    category_file = os.path.join(extracted_dir, f'{category}.json')
                    with open(category_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"  ✓ {category} saved: {len(data) if isinstance(data, list) else 1} items")
    
    def _generate_analysis(self, profile: Dict) -> Dict[str, Any]:
        """Generate analysis and insights from profile."""
        print("\nGenerating analysis...")
        
        analysis = {
            'generated_date': datetime.now().isoformat(),
            'summary': {},
            'gaps': [],
            'recommendations': [],
            'statistics': {}
        }
        
        consolidated = profile['consolidated_data']
        
        # Generate statistics
        analysis['statistics'] = {
            'total_documents': profile['document_count'],
            'document_types': {k: len(v) for k, v in profile['documents_by_type'].items()},
            'skills_count': len(consolidated.get('skills', [])),
            'certifications_count': len(consolidated.get('certifications', [])),
            'experiences_count': len(consolidated.get('experiences', [])),
            'profile_completeness': self._calculate_profile_completeness(profile)
        }
        
        # Generate summary
        analysis['summary'] = {
            'profile_strength': self._assess_profile_strength(profile),
            'key_skills': consolidated.get('skills', [])[:10],  # Top 10 skills
            'recent_experiences': consolidated.get('experiences', [])[:3],  # Most recent 3
            'notable_certifications': consolidated.get('certifications', [])
        }
        
        # Identify gaps
        analysis['gaps'] = self._identify_profile_gaps(profile)
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(profile, analysis['gaps'])
        
        print(f"  ✓ Analysis complete: {len(analysis['recommendations'])} recommendations")
        
        return analysis
    
    def _calculate_profile_completeness(self, profile: Dict) -> int:
        """Calculate profile completeness percentage."""
        consolidated = profile['consolidated_data']
        
        criteria = {
            'personal_info': bool(consolidated.get('personal_info', {})),
            'skills': len(consolidated.get('skills', [])) >= 5,
            'experiences': len(consolidated.get('experiences', [])) >= 1,
            'education': len(consolidated.get('education', [])) >= 1,
            'certifications': len(consolidated.get('certifications', [])) >= 1
        }
        
        completed = sum(1 for criterion in criteria.values() if criterion)
        total = len(criteria)
        
        return int((completed / total) * 100) if total > 0 else 0
    
    def _assess_profile_strength(self, profile: Dict) -> str:
        """Assess overall profile strength."""
        consolidated = profile['consolidated_data']
        
        score = 0
        
        # Skills score
        skills_count = len(consolidated.get('skills', []))
        if skills_count >= 15:
            score += 3
        elif skills_count >= 8:
            score += 2
        elif skills_count >= 3:
            score += 1
        
        # Experience score
        exp_count = len(consolidated.get('experiences', []))
        if exp_count >= 5:
            score += 3
        elif exp_count >= 3:
            score += 2
        elif exp_count >= 1:
            score += 1
        
        # Certification score
        cert_count = len(consolidated.get('certifications', []))
        if cert_count >= 5:
            score += 3
        elif cert_count >= 3:
            score += 2
        elif cert_count >= 1:
            score += 1
        
        # Determine strength level
        if score >= 8:
            return "Excellent"
        elif score >= 5:
            return "Strong"
        elif score >= 3:
            return "Good"
        else:
            return "Developing"
    
    def _identify_profile_gaps(self, profile: Dict) -> List[Dict]:
        """Identify gaps in the profile."""
        gaps = []
        consolidated = profile['consolidated_data']
        
        # Check for missing personal info
        personal_info = consolidated.get('personal_info', {})
        missing_fields = []
        for field in ['name', 'email', 'phone']:
            if field not in personal_info or not personal_info[field]:
                missing_fields.append(field)
        
        if missing_fields:
            gaps.append({
                'category': 'personal_info',
                'issue': f'Missing personal information: {", ".join(missing_fields)}',
                'severity': 'high',
                'suggestion': 'Add missing personal details to your CV'
            })
        
        # Check skills diversity
        skills = consolidated.get('skills', [])
        if len(skills) < 10:
            gaps.append({
                'category': 'skills',
                'issue': f'Only {len(skills)} skills identified (recommended: 10+)',
                'severity': 'medium',
                'suggestion': 'Consider adding more technical and soft skills'
            })
        
        # Check for modern skills
        modern_skills = ['Python', 'AI', 'Machine Learning', 'Cloud', 'Agile', 'DevOps']
        has_modern_skills = any(skill in ' '.join(skills) for skill in modern_skills)
        if not has_modern_skills:
            gaps.append({
                'category': 'skills',
                'issue': 'Missing modern technical skills',
                'severity': 'medium',
                'suggestion': 'Consider adding skills like Python, AI, or Cloud technologies'
            })
        
        # Check certification recency
        certifications = consolidated.get('certifications', [])
        current_year = datetime.now().year
        recent_certs = 0
        
        for cert in certifications:
            # Simple year extraction
            year_match = re.search(r'20\d{2}', cert)
            if year_match:
                year = int(year_match.group())
                if current_year - year <= 5:  # Certifications from last 5 years
                    recent_certs += 1
        
        if recent_certs < 1 and certifications:
            gaps.append({
                'category': 'certifications',
                'issue': 'No recent certifications (last 5 years)',
                'severity': 'medium',
                'suggestion': 'Consider updating or adding new certifications'
            })
        
        return gaps
    
    def _generate_recommendations(self, profile: Dict, gaps: List[Dict]) -> List[Dict]:
        """Generate recommendations based on profile and gaps."""
        recommendations = []
        
        # Add gap-based recommendations
        for gap in gaps:
            recommendations.append({
                'type': 'gap_filling',
                'priority': gap['severity'],
                'action': gap['suggestion'],
                'category': gap['category']
            })
        
        # Add profile-specific recommendations
        consolidated = profile['consolidated_data']
        
        # Skills recommendation
        skills = consolidated.get('skills', [])
        if skills:
            # Recommend grouping skills
            recommendations.append({
                'type': 'organization',
                'priority': 'low',
                'action': 'Group your skills into categories (Technical, Soft, Tools)',
                'category': 'skills'
            })
        
        # Experience recommendation
        experiences = consolidated.get('experiences', [])
        if experiences:
            # Recommend quantifying achievements
            recommendations.append({
                'type': 'enhancement',
                'priority': 'medium',
                'action': 'Add quantifiable achievements to your experience entries',
                'category': 'experiences'
            })
        
        # Document organization recommendation
        doc_types = profile.get('documents_by_type', {})
        if 'cv_resume' in doc_types and len(doc_types['cv_resume']) > 1:
            recommendations.append({
                'type': 'consolidation',
                'priority': 'medium',
                'action': f'Consolidate {len(doc_types["cv_resume"])} CV versions into one master CV',
                'category': 'documents'
            })
        
        return recommendations


def test_processing():
    """Test the document processor with Rajeev's documents."""
    print("="*60)
    print("TESTING DOCUMENT PROCESSOR")
    print("="*60)
    
    processor = DocumentProcessor()
    
    # Test with user 1 (Rajeev)
    result = processor.process_user_documents(1)
    
    print("\n" + "="*60)
    print("PROCESSING RESULTS")
    print("="*60)
    
    if result['status'] == 'success':
        print(f"✓ Successfully processed {result['processed_count']} documents")
        print(f"✓ Found {result['issue_count']} issues")
        print(f"✓ Repository saved to: {result['repository_path']}")
        
        # Show profile summary
        profile = result['profile']
        consolidated = profile['consolidated_data']
        
        print(f"\nPROFILE SUMMARY:")
        print(f"  Personal Info: {consolidated.get('personal_info', {}).get('name', 'Not found')}")
        print(f"  Skills: {len(consolidated.get('skills', []))} skills")
        print(f"  Experiences: {len(consolidated.get('experiences', []))} positions")
        print(f"  Certifications: {len(consolidated.get('certifications', []))} certifications")
        
        # Show analysis
        analysis = result['analysis']
        print(f"\nANALYSIS:")
        print(f"  Profile Strength: {analysis['summary'].get('profile_strength', 'Unknown')}")
        print(f"  Completeness: {analysis['statistics'].get('profile_completeness', 0)}%")
        print(f"  Recommendations: {len(analysis.get('recommendations', []))}")
        
        # Show top recommendations
        if analysis.get('recommendations'):
            print(f"\nTOP RECOMMENDATIONS:")
            for i, rec in enumerate(analysis['recommendations'][:3], 1):
                print(f"  {i}. [{rec['priority'].upper()}] {rec['action']}")
        
        # Show issues if any
        if result['issues']:
            print(f"\nISSUES FOUND:")
            for issue in result['issues'][:5]:  # Show first 5
                print(f"  • {issue['file']}: {issue['error']}")
            if len(result['issues']) > 5:
                print(f"  ... and {len(result['issues']) - 5} more issues")
    
    else:
        print(f"✗ Processing failed: {result.get('message', 'Unknown error')}")
        if result.get('issues'):
            for issue in result['issues']:
                print(f"  • {issue['file']}: {issue['error']}")


if __name__ == "__main__":
    test_processing()