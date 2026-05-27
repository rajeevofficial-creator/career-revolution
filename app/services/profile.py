"""
Profile management service.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict
from datetime import datetime

from app.models.database import UserProfile, UserExperience, UserEducation, UserSkill, UserDocument
from app.services.documents import DocumentService

class ProfileService:
    """Service for managing user profiles."""
    
    def get_user_profile(self, db: Session, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user ID."""
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    def add_skill(self, db: Session, user_id: int, skill_name: str, category: Optional[str] = None, proficiency: Optional[str] = None):
        """Add a skill to user profile."""
        from app.models.database import UserSkill
        skill_name_upper = skill_name.upper().strip()
        
        # Check if already linked
        existing = db.query(UserSkill).filter(
            UserSkill.user_id == user_id, 
            UserSkill.skill_name == skill_name_upper
        ).first()
        
        if not existing:
            user_skill = UserSkill(
                user_id=user_id, 
                skill_name=skill_name_upper,
                category=category,
                proficiency=proficiency
            )
            db.add(user_skill)
        else:
            # Update existing if provided
            if category: existing.category = category
            if proficiency: existing.proficiency = proficiency
            
        db.commit()
        
        # Touch profile updated_at
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.updated_at = datetime.utcnow()
            db.commit()

    def delete_skill(self, db: Session, user_id: int, skill_name: str) -> bool:
        """Remove a skill from user profile."""
        from app.models.database import UserSkill
        # Try both upper and exact match
        skill_name_upper = skill_name.upper().strip()
        user_skill = db.query(UserSkill).filter(
            UserSkill.user_id == user_id, 
            UserSkill.skill_name == skill_name_upper
        ).first()
        
        if not user_skill:
            # Try plain match
            user_skill = db.query(UserSkill).filter(
                UserSkill.user_id == user_id, 
                UserSkill.skill_name == skill_name.strip()
            ).first()

        if user_skill:
            db.delete(user_skill)
            db.commit()
            
            # Touch profile updated_at
            profile = self.get_user_profile(db, user_id)
            if profile:
                profile.updated_at = datetime.utcnow()
                db.commit()
                
            return True
        return False

    def update_user_profile(self, db: Session, user_id: int, profile_data: Dict) -> UserProfile:
        """Update user profile with provided data."""
        profile = self.get_user_profile(db, user_id)
        
        if not profile:
            # Create new profile if it doesn't exist
            profile = UserProfile(user_id=user_id)
            db.add(profile)
        
        # Update profile fields
        for key, value in profile_data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        
        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
        
        return profile
    
    def calculate_profile_completion(self, db: Session, user_id: int) -> int:
        """Calculate profile completion percentage based on multiple factors."""
        profile = self.get_user_profile(db, user_id)
        if not profile:
            return 0
            
        from app.models.database import UserSkill, UserExperience, UserEducation
        
        # Core fields (60% of total)
        core_fields = [
            'phone', 'location', 'linkedin_url', 'summary',
            'current_job_title', 'current_company',
            'desired_job_title', 'desired_industry'
        ]
        
        core_completed = 0
        for field in core_fields:
            if getattr(profile, field, None):
                core_completed += 1
        
        core_weight = (core_completed / len(core_fields)) * 60
        
        # Advanced sections (40% of total)
        has_skills = db.query(UserSkill).filter(UserSkill.user_id == user_id).first() is not None
        has_experience = db.query(UserExperience).filter(UserExperience.user_id == user_id).first() is not None
        has_education = db.query(UserEducation).filter(UserEducation.user_id == user_id).first() is not None
        
        advanced_score = 0
        if has_skills: advanced_score += 15
        if has_experience: advanced_score += 15
        if has_education: advanced_score += 10
        
        return int(core_weight + advanced_score)
    
    def create_or_update_profile(self, db: Session, user_id: int, **kwargs) -> UserProfile:
        """Create or update profile with keyword arguments."""
        profile = self.get_user_profile(db, user_id)
        
        if not profile:
            profile = UserProfile(user_id=user_id, **kwargs)
            db.add(profile)
        else:
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
        
        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
        
        return profile

    def add_skills(self, db: Session, user_id: int, skills: list[str], source_doc_id: Optional[int] = None):
        """Add multiple skills to a user's profile."""
        from app.models.database import UserSkill
        
        for skill_name in skills:
            # Check if skill already exists for user
            existing = db.query(UserSkill).filter(
                UserSkill.user_id == user_id,
                UserSkill.skill_name == skill_name
            ).first()
            
            if not existing:
                db_skill = UserSkill(
                    user_id=user_id,
                    skill_name=skill_name,
                    source_document_id=source_doc_id
                )
                db.add(db_skill)
        
        db.commit()
        
        # Touch profile updated_at
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.updated_at = datetime.utcnow()
            db.commit()

    def add_experiences(self, db: Session, user_id: int, experiences: list[dict], source_doc_id: Optional[int] = None):
        """Add multiple experience entries to a user's profile."""
        from app.models.database import UserExperience
        import re
        
        # Get all existing for the user once to avoid N+1 queries in the loop
        existing_all = db.query(UserExperience).filter(UserExperience.user_id == user_id).all()
        
        def normalize(s):
            if not s: return ""
            # Remove non-alphanumeric for a fuzzy match, but keep it simple enough
            return re.sub(r'[^a-zA-Z0-9]', '', s.lower())

        for exp in experiences:
            company = exp.get('company') or "Unknown Company"
            position = exp.get('title') or "Professional"
            
            # Better deduplication based on normalized strings
            is_duplicate = False
            norm_company = normalize(company)
            norm_position = normalize(position)
            
            for ex in existing_all:
                if normalize(ex.company) == norm_company and normalize(ex.position) == norm_position:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # Use sentinel for missing dates to trigger UI highlight
                start_date = None
                if exp.get('start_date'):
                    try:
                        from app.services.document_analysis import DocumentAnalysisService
                        analyzer = DocumentAnalysisService()
                        start_date = analyzer._parse_date(exp['start_date'])
                    except:
                        pass
                
                if not start_date:
                    start_date = datetime(1900, 1, 1)
                
                end_date = None
                if exp.get('end_date') and exp['end_date'].lower() not in ['present', 'current', 'now']:
                    try:
                        from app.services.document_analysis import DocumentAnalysisService
                        analyzer = DocumentAnalysisService()
                        end_date = analyzer._parse_date(exp['end_date'])
                    except:
                        pass

                db_exp = UserExperience(
                    user_id=user_id,
                    company=company,
                    position=position,
                    description=exp.get('description') or "",
                    start_date=start_date,
                    end_date=end_date,
                    source_document_id=source_doc_id
                )
                db.add(db_exp)
        
        db.commit()
        
        # Touch profile updated_at
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.updated_at = datetime.utcnow()
            db.commit()

    def update_experience(self, db: Session, user_id: int, exp_id: int, exp_data: Dict) -> Optional['UserExperience']:
        """Update a specific experience entry."""
        from app.models.database import UserExperience
        exp = db.query(UserExperience).filter(UserExperience.id == exp_id, UserExperience.user_id == user_id).first()
        if not exp:
            return None
        
        for key, value in exp_data.items():
            if hasattr(exp, key) and value is not None:
                setattr(exp, key, value)
        
        exp.updated_at = datetime.utcnow()
        db.commit()
        
        # Touch profile updated_at
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.updated_at = datetime.utcnow()
            db.commit()
            
        db.refresh(exp)
        return exp

    def delete_experience(self, db: Session, user_id: int, exp_id: int) -> bool:
        """Delete a specific experience entry."""
        from app.models.database import UserExperience
        exp = db.query(UserExperience).filter(UserExperience.id == exp_id, UserExperience.user_id == user_id).first()
        if not exp:
            return False
        
        db.delete(exp)
        db.commit()
        
        # Touch profile updated_at
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.updated_at = datetime.utcnow()
            db.commit()
            
        return True

    def add_educations(self, db: Session, user_id: int, educations: list[dict], source_doc_id: Optional[int] = None):
        """Add multiple education entries with smart de-duplication and master-data prioritization."""
        from app.models.database import UserEducation, UserDocument
        from app.services.document_analysis import DocumentAnalysisService
        import difflib
        
        analyzer = DocumentAnalysisService()
        
        # Check if the source is a certification to prioritize its data
        is_certification = False
        if source_doc_id:
            doc = db.query(UserDocument).filter(UserDocument.id == source_doc_id).first()
            if doc and doc.document_type == 'certification':
                is_certification = True
        
        for edu in educations:
            inst = edu.get('institution') or "Unknown Institution"
            deg = edu.get('degree') or "Degree"
            
            # 1. Fetch all existing education for this user
            all_existing = db.query(UserEducation).filter(UserEducation.user_id == user_id).all()
            
            # 2. Find best match using fuzzy matching on institution
            existing = None
            best_score = 0
            
            for ex in all_existing:
                # Basic normalization for matching
                n_inst = inst.lower().replace('university', '').replace('institute', '').strip()
                n_ex = ex.institution.lower().replace('university', '').replace('institute', '').strip()
                
                # Check for direct inclusion or high similarity
                if n_inst in n_ex or n_ex in n_inst:
                    score = 0.9
                else:
                    score = difflib.SequenceMatcher(None, n_inst, n_ex).ratio()
                
                if score > 0.7 and score > best_score:
                    best_score = score
                    existing = ex
            
            # Parse dates
            grad_date = None
            if edu.get('graduation_date'):
                grad_date = analyzer._parse_date(str(edu['graduation_date']))
            elif edu.get('end_date'):
                grad_date = analyzer._parse_date(str(edu['end_date']))
                
            start_date = None
            if edu.get('start_date'):
                start_date = analyzer._parse_date(str(edu['start_date']))

            if existing:
                # MASTER DATA PRIORITIZATION: 
                # If this document is a certificate, it's the "source of truth"
                if is_certification:
                    if grad_date: existing.end_date = grad_date
                    if start_date: existing.start_date = start_date
                    if deg != "Degree": existing.degree = deg
                    if edu.get('field_of_study'): existing.field_of_study = edu.get('field_of_study')
                    # Update source ID to the certificate as it's now "verified"
                    existing.source_document_id = source_doc_id
                else:
                    # CV enrichment: Only fill if missing
                    if not existing.end_date and grad_date: existing.end_date = grad_date
                    if not existing.start_date and start_date: existing.start_date = start_date
                    if existing.degree == "Degree" and deg != "Degree": existing.degree = deg
                    if not existing.field_of_study and edu.get('field_of_study'):
                        existing.field_of_study = edu.get('field_of_study')
                
                existing.updated_at = datetime.utcnow()
            else:
                db_edu = UserEducation(
                    user_id=user_id,
                    institution=inst,
                    degree=deg,
                    field_of_study=edu.get('field_of_study'),
                    location=edu.get('location'),
                    start_date=start_date,
                    end_date=grad_date,
                    source_document_id=source_doc_id
                )
                db.add(db_edu)
        
        db.commit()
        
        # Touch profile updated_at
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.updated_at = datetime.utcnow()
            db.commit()

    def update_education(self, db: Session, user_id: int, edu_id: int, edu_data: Dict) -> Optional['UserEducation']:
        """Update a specific education entry."""
        from app.models.database import UserEducation
        edu = db.query(UserEducation).filter(UserEducation.id == edu_id, UserEducation.user_id == user_id).first()
        if not edu:
            return None
        
        for key, value in edu_data.items():
            if hasattr(edu, key) and value is not None:
                setattr(edu, key, value)
        
        edu.updated_at = datetime.utcnow()
        db.commit()
        
        # Touch profile updated_at
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.updated_at = datetime.utcnow()
            db.commit()
            
        db.refresh(edu)
        return edu

    def delete_education(self, db: Session, user_id: int, edu_id: int) -> bool:
        """Delete a specific education entry."""
        from app.models.database import UserEducation
        edu = db.query(UserEducation).filter(UserEducation.id == edu_id, UserEducation.user_id == user_id).first()
        if not edu:
            return False
        
        db.delete(edu)
        db.commit()
        
        # Touch profile updated_at
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.updated_at = datetime.utcnow()
            db.commit()
            
        return True
    def clear_profile_data(self, db: Session, user_id: int):
        """Reset all profile data and delete all documents for a fresh start."""
        from app.models.database import UserExperience, UserEducation, UserSkill, UserDocument
        from app.services.documents import DocumentService
        
        # 1. Delete Experience
        db.query(UserExperience).filter(UserExperience.user_id == user_id).delete()
        
        # 2. Delete Education
        db.query(UserEducation).filter(UserEducation.user_id == user_id).delete()
        
        # 3. Delete Skills
        db.query(UserSkill).filter(UserSkill.user_id == user_id).delete()
        
        # 4. Delete Documents (using document service to also remove files)
        doc_service = DocumentService()
        documents = db.query(UserDocument).filter(UserDocument.user_id == user_id).all()
        for doc in documents:
            doc_service.delete_document(db, doc.id, user_id)
            
        # 5. Reset Profile metadata
        profile = self.get_user_profile(db, user_id)
        if profile:
            profile.summary = None
            profile.phone = None
            profile.location = None
            profile.linkedin_url = None
            profile.github_url = None
            profile.portfolio_url = None
            profile.current_job_title = None
            profile.current_company = None
            profile.desired_job_title = None
            profile.desired_industry = None
            profile.desired_location = None
            profile.salary_expectation = None
            profile.notice_period = None
            profile.updated_at = datetime.utcnow()
            
        db.commit()

