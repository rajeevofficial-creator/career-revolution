import asyncio
import sys
import logging

# Windows-specific fix for Playwright/Subprocess: Use ProactorEventLoop
if sys.platform == 'win32':
    try:
        from asyncio import WindowsProactorEventLoopPolicy
        asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
        # Disable future overrides to prevent uvicorn child process from resetting to Selector
        asyncio.set_event_loop_policy = lambda policy: None
    except Exception:
        pass

# Load .env FIRST before anything reads os.getenv()
from dotenv import load_dotenv
load_dotenv(override=True)

"""
Career Revolution - Main FastAPI application.
"""

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Response, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Optional, Dict, Any, List
import os
import json

from app.models.database import get_db, init_db, User, UserDocument, UserProfile, JobOpportunity, JobSource, JobApplication, JobMatch
from sqlalchemy import or_, and_, func, not_
from app.models.schemas import (
    UserCreate, UserResponse, Token, UserLogin, 
    ProfileResponse, DocumentCreate, DocumentResponse, DocumentType,
    UserDashboard, LinkedInExtractionResult, LinkedInAnalysisOptions,
    LinkedInAnalysisResult, LinkedInStatus, LinkedInURLUpdate,
    ExperienceUpdate, EducationUpdate, ExperienceResponse, EducationResponse,
    JobSourceBase, JobSourceCreate, JobSourceResponse,
    JobApplicationBase, JobApplicationCreate, JobApplicationResponse
)
from pydantic import BaseModel, EmailStr, Field
from app.services.auth import (
    authenticate_user, create_access_token, create_user,
    get_user_by_id, update_user_last_login, verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.documents import DocumentService
from app.services.profile import ProfileService
from app.services.password_reset import PasswordResetService

# Import Agents
try:
    from agents.job_search_agent.job_finder_agent import JobFinderAgent
except ImportError as e:
    print(f"Warning: Could not import JobFinderAgent: {e}")
    JobFinderAgent = None

try:
    from agents.job_search_agent.job_sourcing_agent import JobSourcingAgent
except ImportError as e:
    print(f"Warning: Could not import JobSourcingAgent: {e}")
    JobSourcingAgent = None

try:
    from agents.job_preparation_agent import JobPreparationAgent
except ImportError as e:
    print(f"Warning: Could not import JobPreparationAgent: {e}")
    JobPreparationAgent = None

try:
    from agents.auto_apply_agent import AutoApplyAgent
except ImportError as e:
    print(f"Warning: Could not import AutoApplyAgent: {e}")
    AutoApplyAgent = None

try:
    from agents.application_tracking_agent.application_tracking_agent import ApplicationTrackingAgent
except ImportError as e:
    print(f"Warning: Could not import ApplicationTrackingAgent: {e}")
    ApplicationTrackingAgent = None

try:
    from agents.social_profile_agent.social_profile_agent import SocialProfileAgent
except ImportError as e:
    print(f"Warning: Could not import SocialProfileAgent: {e}")
    SocialProfileAgent = None

# Initialize Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI app
app = FastAPI(
    title="Career Revolution API",
    description="AI-powered career portal for job seekers",
    version="1.0.0"
)

# PERMISSIVE CORS for local development (supports file:/// access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler with CORS support
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"GLOBAL EXCEPTION: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Dependency to get current user from token
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    user = get_user_by_id(db, token_data.user_id)
    if user is None:
        raise credentials_exception
    
    return user

# Initialize services
document_service = DocumentService()
profile_service = ProfileService()

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    init_db()
    print("Career Revolution API started")
    print(f"Upload directory: {os.path.abspath(document_service.upload_base_path)}")
    
    # Check for Gemini API Key
    from app.config import settings
    if not settings.gemini_api_key:
        print("\n" + "="*60)
        print("WARNING: GEMINI_API_KEY not found in environment.")
        print("Enhanced document extraction (OCR/AI) will be disabled.")
        print("Set GEMINI_API_KEY in .env to enable high-fidelity parsing.")
        print("="*60 + "\n")

# Health check endpoint (moved off / so StaticFiles can serve index.html at root)
@app.get("/health")
async def root():
    """Health check endpoint."""
    return {
        "message": "Career Revolution API",
        "version": "1.0.0",
        "status": "running"
    }

# Authentication endpoints
@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = create_user(db, user_data)
    return user

@app.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login user and return access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    update_user_last_login(db, user.id)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# User profile endpoints
@app.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile."""
    profile = profile_service.get_user_profile(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile

@app.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: dict,  # Will accept any profile fields
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile."""
    profile = profile_service.update_user_profile(db, current_user.id, profile_data)
    return profile

@app.post("/profile/skills", status_code=status.HTTP_201_CREATED)
async def add_skill(
    skill_data: dict, # {"name": "Python", "category": "technical", "proficiency": "expert"}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a skill to profile."""
    if 'name' not in skill_data:
        raise HTTPException(status_code=400, detail="Skill name required")
    
    profile_service.add_skill(
        db, 
        current_user.id, 
        skill_data['name'], 
        category=skill_data.get('category'),
        proficiency=skill_data.get('proficiency')
    )
    return {"message": "Skill added"}

@app.delete("/profile/skills/{skill_name}")
async def delete_skill(
    skill_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a skill from profile."""
    if profile_service.delete_skill(db, current_user.id, skill_name):
        return {"message": "Skill removed"}
    raise HTTPException(status_code=404, detail="Skill not found")

@app.put("/profile/experience/{exp_id}", response_model=ExperienceResponse)
async def update_experience(
    exp_id: int,
    exp_data: ExperienceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific experience entry."""
    exp = profile_service.update_experience(db, current_user.id, exp_id, exp_data.dict(exclude_unset=True))
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")
    return exp

@app.delete("/profile/experience/{exp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(
    exp_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific experience entry."""
    if not profile_service.delete_experience(db, current_user.id, exp_id):
        raise HTTPException(status_code=404, detail="Experience not found")
    return None

@app.put("/profile/education/{edu_id}", response_model=EducationResponse)
async def update_education(
    edu_id: int,
    edu_data: EducationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific education entry."""
    edu = profile_service.update_education(db, current_user.id, edu_id, edu_data.dict(exclude_unset=True))
    if not edu:
        raise HTTPException(status_code=404, detail="Education not found")
    return edu

@app.delete("/profile/education/{edu_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_education(
    edu_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific education entry."""
    if not profile_service.delete_education(db, current_user.id, edu_id):
        raise HTTPException(status_code=404, detail="Education not found")
    return None

@app.post("/profile/reset")
async def reset_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset all profile data and delete all documents."""
    profile_service.clear_profile_data(db, current_user.id)
    return {"message": "Profile reset successfully"}

# Document endpoints
@app.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document (CV, certification, etc.)."""
    # Validate document type
    try:
        from app.models.schemas import DocumentType
        doc_type = DocumentType(document_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Must be one of: {[t.value for t in DocumentType]}"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Create document data
    document_data = DocumentCreate(
        document_type=doc_type,
        original_filename=file.filename
    )
    
    # Save document
    document = document_service.save_document(
        db=db,
        user_id=current_user.id,
        document_data=document_data,
        file_content=file_content,
        original_filename=file.filename
    )
    
    # If it's a profile picture, automatically update the user profile
    if doc_type == DocumentType.PROFILE_PICTURE:
        # Use relative URL that will be served by our StaticFiles mount
        profile_picture_url = f"/uploads/{current_user.id}/profile_picture/{document.stored_filename}"
        profile_service.update_user_profile(db, current_user.id, {"profile_picture_url": profile_picture_url})
    
    return document

@app.post("/documents/upload-multiple", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_multiple_documents(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload multiple documents at once."""
    from app.models.schemas import DocumentType
    
    uploaded_documents = []
    failed_uploads = []
    
    for file in files:
        try:
            # Determine document type from filename
            filename_lower = file.filename.lower()
            if any(ext in filename_lower for ext in ['.pdf', '.doc', '.docx', '.txt']):
                if 'cv' in filename_lower or 'resume' in filename_lower:
                    doc_type = DocumentType.RESUME
                elif 'certif' in filename_lower or 'license' in filename_lower:
                    doc_type = DocumentType.CERTIFICATION
                elif 'transcript' in filename_lower:
                    doc_type = DocumentType.OTHER  # No transcript type, use OTHER
                elif 'cover' in filename_lower:
                    doc_type = DocumentType.OTHER  # No cover letter type, use OTHER
                else:
                    doc_type = DocumentType.OTHER
            elif any(ext in filename_lower for ext in ['.png', '.jpg', '.jpeg']):
                doc_type = DocumentType.OTHER  # No image type, use OTHER
            else:
                doc_type = DocumentType.OTHER
            
            # Read file content
            file_content = await file.read()
            
            # Create document data
            document_data = DocumentCreate(
                document_type=doc_type,
                original_filename=file.filename
            )
            
            # Save document
            document = document_service.save_document(
                db=db,
                user_id=current_user.id,
                document_data=document_data,
                file_content=file_content,
                original_filename=file.filename
            )
            
            uploaded_documents.append({
                "id": document.id,
                "filename": file.filename,
                "type": doc_type.value,
                "status": "success"
            })
            
        except Exception as e:
            failed_uploads.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "uploaded_count": len(uploaded_documents),
        "failed_count": len(failed_uploads),
        "uploaded_documents": uploaded_documents,
        "failed_uploads": failed_uploads
    }

@app.get("/documents", response_model=list[DocumentResponse])
async def get_documents(
    document_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for current user."""
    documents = document_service.get_user_documents(db, current_user.id, document_type)
    return documents

@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific document."""
    document = document_service.get_document_by_id(db, document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document

@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document."""
    success = document_service.delete_document(db, document_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

# Advanced document analysis endpoints
from app.services.document_analysis import DocumentAnalysisService
document_analysis_service = DocumentAnalysisService()

class FolderAnalysisRequest(BaseModel):
    """Request model for folder analysis."""
    folder_path: Optional[str] = None  # For server-side folder analysis
    analysis_options: Optional[Dict[str, Any]] = None

class DocumentAnalysisResult(BaseModel):
    """Response model for document analysis."""
    filename: str
    document_type: str
    analysis_complete: bool
    skills: List[str] = []
    linkedin_urls: List[str] = []
    error: Optional[str] = None

class FolderAnalysisResult(BaseModel):
    """Response model for folder analysis."""
    total_files: int
    successful_analyses: int
    failed_analyses: int
    document_types: Dict[str, int]
    all_skills: List[str]
    all_linkedin_urls: List[str]
    personal_info_consolidated: Dict[str, List[str]]
    summary: Dict[str, Any]
    individual_results: List[DocumentAnalysisResult]
    profile_update_suggestions: Dict[str, Any]

@app.post("/documents/analyze-folder", response_model=FolderAnalysisResult)
async def analyze_folder(
    analysis_request: FolderAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze a folder of documents (server-side).
    Note: In production, this would handle uploaded folder contents.
    For now, it analyzes a folder path on the server.
    """
    if not analysis_request.folder_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder path is required"
        )
    
    # Check if folder exists
    if not os.path.exists(analysis_request.folder_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder not found: {analysis_request.folder_path}"
        )
    
    # Analyze folder
    analysis_results = document_analysis_service.analyze_folder(analysis_request.folder_path)
    
    if not analysis_results.get('analysis_complete', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=analysis_results.get('error', 'Folder analysis failed')
        )
    
    # Save analysis results to user profile
    save_result = document_analysis_service.save_analysis_to_profile(
        db, current_user.id, analysis_results
    )
    
    # Update user's LinkedIn URL if found
    if analysis_results.get('all_linkedin_urls'):
        personal_urls = [url for url in analysis_results['all_linkedin_urls'] if '/in/' in url]
        if personal_urls:
            # Update user profile with LinkedIn URL
            from app.services.profile import ProfileService
            profile_service = ProfileService()
            profile_service.update_user_profile(db, current_user.id, {
                'linkedin_url': personal_urls[0]
            })
    
    return analysis_results

from fastapi import BackgroundTasks
from app.models.database import SessionLocal

def _process_single_document(document_id: int, user_id: int):
    """Worker function to process a single document in a separate thread."""
    db = SessionLocal()
    try:
        from app.services.auth import get_user_by_id
        document = document_service.get_document_by_id(db, document_id, user_id)
        if not document or document.is_processed:
            return
            
        # Update status to processing
        document_service.update_document_processing_status(db, document.id, "processing")
        
        file_path = document.file_path
        if file_path and os.path.exists(file_path):
            import asyncio
            result = asyncio.run(document_analysis_service.analyze_document(file_path, document.original_filename))
            
            if result.get('analysis_complete', False):
                # Save extracted data
                import json
                extracted_json = json.dumps(result, default=str)
                document_service.update_document_processing_status(db, document.id, "completed", extracted_data=extracted_json)
                
                # Update profile
                profile_service.add_skills(db, user_id, result.get('skills', []), source_doc_id=document.id)
                profile_service.add_experiences(db, user_id, result.get('experience', []), source_doc_id=document.id)
                
                # Merge education and certifications as requested by user
                education_entries = result.get('education', [])
                certification_entries = result.get('certifications', [])
                
                # Convert certifications to education format if not already
                for cert in certification_entries:
                    education_entries.append({
                        'institution': cert.get('issuer') or cert.get('name') or "Certificate",
                        'degree': cert.get('name') or "Certification",
                        'description': cert.get('description'),
                        'start_date': cert.get('date')
                    })
                
                profile_service.add_educations(db, user_id, education_entries, source_doc_id=document.id)
                
                # Update summary and contact info
                personal_info = result.get('personal_info', {})
                profile_updates = {}
                
                if personal_info.get('summary'):
                    profile_updates['summary'] = personal_info['summary']
                if personal_info.get('phone'):
                    profile_updates['phone'] = personal_info['phone']
                if personal_info.get('location'):
                    profile_updates['location'] = personal_info['location']
                if personal_info.get('sector'):
                    profile_updates['sector'] = personal_info['sector']
                if personal_info.get('industry'):
                    profile_updates['industry'] = personal_info['industry']
                
                # Update LinkedIn if found (check both LLM field and heuristic list)
                linkedin_url = personal_info.get('linkedin_url')
                if not linkedin_url:
                    heuristic_urls = result.get('linkedin_urls', [])
                    personal_urls = [url for url in heuristic_urls if '/in/' in url]
                    if personal_urls:
                        linkedin_url = personal_urls[0]
                
                if linkedin_url:
                    profile_updates['linkedin_url'] = linkedin_url
                
                if profile_updates:
                    profile_service.update_user_profile(db, user_id, profile_updates)
                
                # Update User table for name
                if personal_info.get('name'):
                    from app.models.database import User
                    db.query(User).filter(User.id == user_id).update({'full_name': personal_info['name']})
                    db.commit()
            else:
                document_service.update_document_processing_status(db, document.id, "failed", result.get('error', 'Analysis failed'))
        else:
            document_service.update_document_processing_status(db, document.id, "failed", "File not found")
            
    except Exception as e:
        print(f"Error processing document {document_id}: {e}")
        try:
            document_service.update_document_processing_status(db, document_id, "failed", str(e))
        except:
            pass
    finally:
        db.close()

def _run_analysis_background(user_id: int):
    """Run document analysis in the background using parallel workers."""
    import concurrent.futures
    db = SessionLocal()
    try:
        documents = document_service.get_user_documents(db, user_id)
        pending_docs = [doc.id for doc in documents if not doc.is_processed]
        
        if not pending_docs:
            return
            
        # Process in parallel (limit to 4 concurrent tasks to avoid resource exhaustion)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_process_single_document, doc_id, user_id) for doc_id in pending_docs]
            concurrent.futures.wait(futures)
            
    except Exception as e:
        print(f"Background analysis manager error: {e}")
    finally:
        db.close()


@app.post("/documents/analyze-uploaded")
async def analyze_uploaded_documents(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Queue analysis of all uploaded documents for the current user.
    """
    documents = document_service.get_user_documents(db, current_user.id)
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found for analysis"
        )
    
    # Run in background to prevent timeout
    background_tasks.add_task(_run_analysis_background, current_user.id)
    
    return {"message": "Background analysis started", "documents_queued": len(documents)}

# Dashboard endpoint
@app.get("/dashboard", response_model=UserDashboard)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user dashboard with all data."""
    # Get user data
    profile = profile_service.get_user_profile(db, current_user.id)
    
    # Get documents
    documents = document_service.get_user_documents(db, current_user.id)
    
    # Fetch real data for dashboard
    from app.models.database import UserSkill, UserExperience, UserEducation
    skills = db.query(UserSkill).filter(UserSkill.user_id == current_user.id).all()
    experiences = db.query(UserExperience).filter(UserExperience.user_id == current_user.id).all()
    educations = db.query(UserEducation).filter(UserEducation.user_id == current_user.id).all()
    
    # Calculate stats
    doc_stats = document_service.get_document_stats(db, current_user.id)
    profile_completion = profile_service.calculate_profile_completion(db, current_user.id)
    
    # Get job matches count (simulated matching based on skills for now)
    # In a full implementation, this calls JobSearchAgent.search_jobs()
    job_match_count = len(skills) * 3 if skills else 0
    if job_match_count > 50: job_match_count = 42 # Cap for realism in mock
    
    stats = {
        "total_documents": doc_stats["total_documents"],
        "processed_documents": doc_stats["processed_documents"],
        "total_skills": len(skills),
        "total_experience": len(experiences),
        "job_matches": job_match_count,
        "profile_completion": profile_completion
    }
    
    return UserDashboard(
        user=current_user,
        profile=profile,
        documents=documents,
        skills=skills,
        experiences=experiences,
        educations=educations,
        stats=stats
    )

# LinkedIn endpoints
from app.services.linkedin_service import LinkedInService

linkedin_service = LinkedInService()

@app.post("/linkedin/extract/{document_id}", response_model=LinkedInExtractionResult)
async def extract_linkedin_from_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract LinkedIn URLs from a specific document."""
    # First check if document belongs to user
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    result = linkedin_service.process_document_for_linkedin(db, document_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result

@app.post("/linkedin/extract-all", response_model=dict)
async def extract_linkedin_from_all_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract LinkedIn URLs from all unprocessed documents for the current user."""
    result = linkedin_service.process_all_user_documents(db, current_user.id)
    return result

@app.get("/linkedin/profile/status", response_model=LinkedInStatus)
async def get_linkedin_profile_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get LinkedIn profile URL status for the current user."""
    status_data = linkedin_service.get_user_linkedin_status(db, current_user.id)
    return status_data

@app.put("/linkedin/update-url", response_model=dict)
async def update_linkedin_url(
    linkedin_data: LinkedInURLUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually update LinkedIn URL for the current user."""
    result = linkedin_service.update_linkedin_url(db, current_user.id, linkedin_data.linkedin_url)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result

@app.post("/linkedin/analyze", response_model=LinkedInAnalysisResult)
async def analyze_linkedin_profile(
    analysis_options: LinkedInAnalysisOptions = LinkedInAnalysisOptions(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze LinkedIn profile and generate recommendations."""
    # Get user's LinkedIn URL
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if not profile or not profile.linkedin_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No LinkedIn URL found. Please upload documents or add your LinkedIn URL manually."
        )
    
    # For now, return a placeholder response
    # In Phase 2B, this will integrate with the existing LinkedIn analysis tools
    return {
        "success": True,
        "linkedin_url": profile.linkedin_url,
        "analysis_type": analysis_options.analysis_type,
        "score": 75,
        "strengths": [
            "Strong industry experience",
            "Good network connections",
            "Complete profile sections"
        ],
        "weaknesses": [
            "Limited content activity",
            "Could use more keywords",
            "Profile photo could be more professional"
        ],
        "recommendations": [
            "Add more industry-specific keywords to your headline",
            "Share relevant articles weekly",
            "Connect with 5 industry leaders this week"
        ],
        "optimization_plan": "90-day optimization plan available",
        "generated_templates": [],
        "report_path": None,
        "error": None
    }

# Email verification endpoints
@app.post("/auth/send-verification-email")
async def send_verification_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send verification email to current user."""
    from app.services.real_email_service import create_verification_token, EmailService
    
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    verification_token = create_verification_token(db, current_user.id)
    
    # Try to send real email
    email_service = EmailService()
    email_sent = email_service.send_verification_email(
        current_user.email, 
        current_user.full_name or current_user.email, 
        verification_token.token
    )
    
    if email_sent:
        return {"message": "Verification email sent", "email_sent": True}
    else:
        # Fallback to simulated email
        from app.services.email_service import send_verification_email as send_simulated_email
        send_simulated_email(current_user.email, current_user.full_name or current_user.email, verification_token.token)
        return {"message": "Verification email sent (simulated - check console)", "email_sent": False}

@app.get("/auth/verify-email")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify email using token."""
    from app.services.real_email_service import verify_token, EmailService
    
    verification_token = verify_token(db, token)
    if not verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Mark user as verified
    user = db.query(User).filter(User.id == verification_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_verified = True
    db.commit()
    
    # Send welcome email
    email_service = EmailService()
    email_sent = email_service.send_welcome_email(user.email, user.full_name or user.email)
    
    if not email_sent:
        # Fallback to simulated email
        from app.services.email_service import send_welcome_email as send_simulated_welcome
        send_simulated_welcome(user.email, user.full_name or user.email)
    
    return {"message": "Email verified successfully", "email_sent": email_sent}

@app.get("/auth/check-verification")
async def check_verification(
    current_user: User = Depends(get_current_user)
):
    """Check if current user's email is verified."""
    return {"is_verified": current_user.is_verified}

# Password reset endpoints
password_reset_service = PasswordResetService()
print("Password reset service initialized")

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

@app.post("/auth/request-password-reset")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request a password reset link."""
    success, message = password_reset_service.request_password_reset(db, reset_request.email)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"message": message}

@app.post("/auth/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password using a valid token."""
    success, message = password_reset_service.reset_password(db, reset_data.token, reset_data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"message": message}

@app.post("/auth/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user."""
    success, message = password_reset_service.change_password(
        db, current_user.id, password_data.current_password, password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"message": message}

@app.get("/auth/validate-reset-token/{token}")
async def validate_reset_token(
    token: str,
    db: Session = Depends(get_db)
):
    """Validate a password reset token."""
    valid, user, message = password_reset_service.validate_reset_token(db, token)
    
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {
        "valid": True,
        "email": user.email,
        "message": "Token is valid"
    }

# Admin endpoints (for development)
@app.get("/admin/users", response_model=list[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    # In production, add admin authentication
):
    """Get all users (admin only)."""
    users = db.query(User).all()
    return users

@app.post("/admin/verify-email/{user_id}")
async def admin_verify_email(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Admin endpoint to verify a user's email (development only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_verified = True
    db.commit()
    
    return {"message": f"Email verified for user: {user.email}", "user_id": user.id, "email": user.email}

@app.post("/admin/reset-password/{user_id}")
async def admin_reset_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Admin endpoint to reset a user's password (development only)."""
    from app.services.auth import get_password_hash
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.password_hash = get_password_hash(new_password)
    db.commit()
    
    return {"message": f"Password reset for user: {user.email}", "user_id": user.id, "email": user.email}


# ── LinkedIn Browser Endpoints ────────────────────────────────────────────────

from app.services.linkedin_browser import LinkedInBrowserService as _LIBrowser
_li_browser = _LIBrowser()

class LinkedInConnectRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

class LinkedInSearchRequest(BaseModel):
    keyword: str = ""
    max_jobs: int = 50

@app.get("/linkedin/status")
async def linkedin_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return current LinkedIn session status for this user."""
    return _li_browser.session_status(db, current_user.id)

@app.post("/linkedin/connect")
async def linkedin_connect(
    req: LinkedInConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save credentials (if provided) and immediately attempt login."""
    if req.email and req.password:
        _li_browser.save_credentials(db, current_user.id, req.email, req.password)
    else:
        from app.models.database import LinkedInSession
        session = db.query(LinkedInSession).filter(LinkedInSession.user_id == current_user.id).first()
        if not session or not session.linkedin_email_enc or not session.linkedin_pw_enc:
            raise HTTPException(status_code=400, detail="No credentials provided or stored. Please enter your LinkedIn email and password.")

    success, message = await _li_browser.login(db, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "connected", "message": message}

@app.post("/linkedin/disconnect")
async def linkedin_disconnect(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear the LinkedIn session."""
    _li_browser.disconnect(db, current_user.id)
    return {"status": "disconnected"}

@app.post("/linkedin/fetch-jobs")
async def linkedin_fetch_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch 'Jobs for You' from LinkedIn using the stored session."""
    success, message, new_count = await _li_browser.fetch_jobs(
        db, current_user.id, fetch_source="jobs_for_you"
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "message": message, "new_jobs": new_count}

@app.post("/linkedin/search-jobs")
async def linkedin_search_jobs(
    req: LinkedInSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search LinkedIn jobs by keyword for Switzerland."""
    success, message, new_count = await _li_browser.fetch_jobs(
        db, current_user.id,
        keyword=req.keyword,
        max_jobs=req.max_jobs,
        fetch_source="search",
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "message": message, "new_jobs": new_count}

@app.get("/linkedin/jobs")
async def linkedin_get_jobs(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated LinkedIn jobs for this user."""
    return _li_browser.get_jobs(db, current_user.id, page=page, size=size)

# --- NEW AGENT ENDPOINTS ---
def _derive_country(profile) -> str:
    """Extract a normalised country string from a user profile."""
    if not profile or not profile.location:
        return "Switzerland"
    loc = profile.location.lower()
    if any(k in loc for k in ["switzerland","schweiz","suisse","svizzera","ch-",
                                "zurich","zürich","basel","geneva","genf",
                                "lausanne","bern","lugano","zug"]):
        return "Switzerland"
    if any(k in loc for k in ["germany","deutschland","berlin","munich","münchen",
                                "hamburg","frankfurt"]):
        return "Germany"
    if any(k in loc for k in ["france","frankreich","paris","lyon","marseille"]):
        return "France"
    if any(k in loc for k in ["usa","united states","america","new york",
                                "san francisco","chicago"]):
        return "USA"
    if any(k in loc for k in ["india","bharat","bangalore","bengaluru","mumbai",
                                "delhi","pune","hyderabad"]):
        return "India"
    if any(k in loc for k in ["netherlands","holland","amsterdam","rotterdam"]):
        return "Netherlands"
    if any(k in loc for k in ["united kingdom","uk","england","london","manchester"]):
        return "UK"
    # Last resort: take the last comma-separated segment as the country
    if "," in profile.location:
        return profile.location.rsplit(",", 1)[-1].strip()
    return profile.location.strip()


# ── Phase 1: Raw job ingestion ────────────────────────────────────────────────
@app.post("/jobs/refresh")
async def refresh_jobs(
    country: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Phase 1 — download all jobs from validated sources for a country."""
    if JobFinderAgent is None:
        raise HTTPException(status_code=503, detail="Job Finder Agent not available")

    if not country:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        country = _derive_country(profile)

    agent = JobFinderAgent(db)
    return await agent.ingest_jobs(country)


# ── Phase 2: User alignment ───────────────────────────────────────────────────
@app.post("/jobs/align")
async def align_jobs(
    deep_check: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Phase 2 — score recent jobs against user profile, create JobMatch records."""
    if JobFinderAgent is None:
        raise HTTPException(status_code=503, detail="Job Finder Agent not available")

    agent = JobFinderAgent(db)
    return await agent.align_jobs_to_user(current_user.id, deep_check=deep_check)


@app.post("/jobs/score")
async def score_jobs(
    source_country: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Target Scoring — re-score existing jobs against the user profile."""
    if JobFinderAgent is None:
        raise HTTPException(status_code=503, detail="Job Finder Agent not available")

    if not source_country:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        source_country = _derive_country(profile)

    agent = JobFinderAgent(db)
    result = await agent.score_jobs_for_user(current_user.id, source_country=source_country)
    return result


@app.get("/jobs/sources/countries")
async def get_supported_countries(
    current_user: User = Depends(get_current_user)
):
    """
    Return the list of countries supported for job source sync.
    The frontend uses this to populate the country dropdown shown to admins
    before triggering Sync & Refine Sources.
    """
    countries = [
        {"code": "CH", "name": "Switzerland"},
        {"code": "DE", "name": "Germany"},
        {"code": "AT", "name": "Austria"},
        {"code": "GB", "name": "United Kingdom"},
        {"code": "US", "name": "United States"},
        {"code": "FR", "name": "France"},
        {"code": "NL", "name": "Netherlands"},
        {"code": "SE", "name": "Sweden"},
        {"code": "DK", "name": "Denmark"},
        {"code": "NO", "name": "Norway"},
        {"code": "FI", "name": "Finland"},
        {"code": "IE", "name": "Ireland"},
        {"code": "LU", "name": "Luxembourg"},
        {"code": "BE", "name": "Belgium"},
        {"code": "ES", "name": "Spain"},
        {"code": "IT", "name": "Italy"},
        {"code": "PL", "name": "Poland"},
        {"code": "SG", "name": "Singapore"},
        {"code": "AU", "name": "Australia"},
        {"code": "CA", "name": "Canada"},
    ]
    return {"countries": countries}


@app.post("/jobs/sources/run")
async def refresh_sources(
    country: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger the Job Sourcing Agent to discover and vet job sources for the given country.

    `country` is required — select from /jobs/sources/countries before calling this.
    The country must be the full country name (e.g. 'Switzerland'), not a code.
    """
    if not country or not country.strip():
        raise HTTPException(status_code=400, detail="country is required. Fetch /jobs/sources/countries for the list.")
    if JobSourcingAgent is None:
        raise HTTPException(status_code=503, detail="Job Sourcing Agent not available")

    agent = JobSourcingAgent(db)
    result = await agent.run_sourcing_pipeline(current_user.id, country=country.strip(), force_update=force)
    return result

@app.post("/jobs/sources/vet")
async def vet_job_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refine existing job sources to find exact career pages.
    """
    if JobSourcingAgent is None:
        raise HTTPException(status_code=503, detail="Job Sourcing Agent not available")
    
    agent = JobSourcingAgent(db)
    result = await agent.vet_all_sources()
    return result

@app.get("/jobs/sources", response_model=List[JobSourceResponse])
async def get_job_sources(
    country: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List job sources, optionally filtered by country."""
    try:
        query = db.query(JobSource)
        if country:
            query = query.filter(JobSource.country == country)
        sources = query.order_by(JobSource.quality_score.desc()).all()
        logger.info(f"Returning {len(sources)} sources (country={country}) for user {current_user.id}")
        return sources
    except Exception as e:
        logger.error(f"Error in get_job_sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/sources", response_model=JobSourceResponse)
async def create_job_source(
    source_data: JobSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new job source."""
    # Check if URL already exists
    existing = db.query(JobSource).filter(JobSource.url == source_data.url).first()
    if existing:
        # Update existing
        existing.name = source_data.name
        existing.source_type = source_data.source_type
        existing.description = source_data.description
        existing.is_active = source_data.is_active
        if source_data.tags:
            existing.tags = json.dumps(source_data.tags)
    else:
        # Create new
        new_source = JobSource(
            name=source_data.name,
            url=source_data.url,
            source_type=source_data.source_type,
            description=source_data.description,
            is_active=source_data.is_active,
            tags=json.dumps(source_data.tags) if source_data.tags else None
        )
        db.add(new_source)
        existing = new_source
    
    db.commit()
    db.refresh(existing)
    return existing

@app.delete("/jobs/sources/{source_id}")
async def delete_job_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a job source."""
    source = db.query(JobSource).filter(JobSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    db.delete(source)
    db.commit()
    return {"message": "Source deleted successfully"}

@app.patch("/jobs/sources/{source_id}/toggle")
async def toggle_job_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle the is_active status of a job source."""
    source = db.query(JobSource).filter(JobSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source.is_active = not source.is_active
    db.commit()
    db.refresh(source)
    return source

@app.get("/jobs/search")
async def search_jobs(
    page: int = 1,
    size: int = 20,
    filter_type: str = "all",
    location_filter: Optional[str] = None,
    q: Optional[str] = None,
    job_types: Optional[List[str]] = Query(None),
    work_modes: Optional[List[str]] = Query(None),
    experience_level: Optional[str] = None,
    days_old: int = 0,
    source_country: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query persisted jobs — pure read, no ingestion.
    Use POST /jobs/refresh then POST /jobs/align to populate data.
    """
    # Derive country from profile if not supplied
    if not source_country:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        source_country = _derive_country(profile)
    
    # Base query: Join with JobMatch to get user-specific scores
    if filter_type == "recommended":
        query = db.query(JobOpportunity, JobMatch.relevance_score.label('match_score'), JobMatch.is_verified.label('match_verified')).join(
            JobMatch, 
            JobMatch.job_opportunity_id == JobOpportunity.id
        ).filter(
            JobOpportunity.is_live == True,
            JobMatch.user_id == current_user.id,
            JobMatch.relevance_score >= 25
        ).order_by(JobMatch.relevance_score.desc())
    else:
        query = db.query(JobOpportunity, JobMatch.relevance_score.label('match_score'), JobMatch.is_verified.label('match_verified')).outerjoin(
            JobMatch,
            and_(JobMatch.job_opportunity_id == JobOpportunity.id, JobMatch.user_id == current_user.id)
        ).filter(
            JobOpportunity.is_live == True
        )
        
    # Apply Source-Level Country Filter (Scalability Fix)
    if source_country:
        query = query.join(JobSource, JobOpportunity.source_id == JobSource.id).filter(JobSource.country == source_country)
        
    if filter_type == "recommended":
        query = query.order_by(JobMatch.relevance_score.desc())
    else:
        query = query.order_by(JobOpportunity.first_seen_at.desc())
    
    # Exclude obvious junk titles from existing database records
    junk_titles = ['%zum Main Content%', '%Skip to content%', '%Skip to main content%', '%JavaScript is required%']
    for junk in junk_titles:
        query = query.filter(not_(JobOpportunity.title.ilike(junk)))

    # Apply Recommendations Filter (Use match score only)
    if filter_type == "recommended":
        # Ensure we only count unique jobs even if the join creates duplicates
        query = query.group_by(JobOpportunity.id)

    # Apply Text Search (Title, Company, Description)
    if q:
        query = query.filter(or_(
            JobOpportunity.title.ilike(f"%{q}%"),
            JobOpportunity.company.ilike(f"%{q}%"),
            JobOpportunity.description.ilike(f"%{q}%")
        ))

    # Apply location filter with fuzzy normalization
    if location_filter:
        loc = location_filter.strip().rstrip(' Area')
        filters = [JobOpportunity.location.ilike(f"%{loc}%")]
        
        # Add common variants
        if "geneva" in loc.lower() or "romandie" in loc.lower():
            # Broad search for French-speaking Switzerland (Romandie)
            filters.append(JobOpportunity.location.ilike("%Geneva%"))
            filters.append(JobOpportunity.location.ilike("%Genève%"))
            filters.append(JobOpportunity.location.ilike("%Lausanne%"))
            filters.append(JobOpportunity.location.ilike("%Vaud%"))
            filters.append(JobOpportunity.location.ilike("%Valais%"))
            filters.append(JobOpportunity.location.ilike("%Fribourg%"))
            filters.append(JobOpportunity.location.ilike("%Neuchâtel%"))
            filters.append(JobOpportunity.location.ilike("%Jura%"))
        elif loc.lower() in ['zurich', 'zürich']:
            filters.append(JobOpportunity.location.ilike("%Zürich%"))
            filters.append(JobOpportunity.location.ilike("%Zurich%"))
        if loc.lower() in ['geneva', 'genève']:
            filters.append(JobOpportunity.location.ilike("%Geneva%"))
            filters.append(JobOpportunity.location.ilike("%Genève%"))
            
        query = query.filter(or_(*filters))
    
    # Apply Job Type filter
    if job_types:
        query = query.filter(JobOpportunity.job_type.in_(job_types))
        
    # Apply Work Mode filter
    if work_modes:
        query = query.filter(JobOpportunity.work_mode.in_(work_modes))
        
    # Apply Experience Level filter
    if experience_level:
        query = query.filter(JobOpportunity.experience_level == experience_level)
        
    # Apply Days Old filter
    if days_old > 0:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        query = query.filter(JobOpportunity.first_seen_at >= cutoff)
    
    # Get total count
    total = query.count()
    print(f"DEBUG: found {total} total jobs for this query.")
    
    # Fetch paginated jobs
    jobs = query.offset((page - 1) * size)\
                .limit(size)\
                .all()
    
    # Format and serialize for the frontend
    serialized_jobs = []
    
    for item in jobs:
        # Determine the "job" object and metadata using the most reliable method available
        if hasattr(item, '_mapping'):
            row = item._mapping
            job = row.get('JobOpportunity', item[0])
            score = row.get('match_score', 0)
            is_verified_match = row.get('match_verified', False)
        elif isinstance(item, (tuple, list)) or hasattr(item, '__iter__'):
            job = item[0]
            score = item[1] if len(item) > 1 else 0
            is_verified_match = item[2] if len(item) > 2 else False
        else:
            job = item
            score = getattr(job, 'relevance_score', 0)
            is_verified_match = getattr(job, 'is_verified', False)

        # Defensive field extraction helper for model instances or rows
        def get_f(field, default=None):
            # Try from the job object (Model instance)
            val = getattr(job, field, None)
            if val is not None: return val
            # Try from the row mapping if available
            if hasattr(item, '_mapping'):
                val = item._mapping.get(f"job_opportunities_{field}") or item._mapping.get(field)
                if val is not None: return val
            return default

        # Defensive skills extraction
        skills_raw = get_f('skills_required')
        skills_matched = []
        if skills_raw:
            try:
                if isinstance(skills_raw, str):
                    skills_matched = json.loads(skills_raw)
                elif isinstance(skills_raw, list):
                    skills_matched = skills_raw
            except Exception:
                skills_matched = []

        # Robust URL construction: if direct link is missing, provide a search fallback
        target_url = get_f('application_url')
        if not target_url or target_url == '#':
            from urllib.parse import quote_plus
            target_url = f"https://www.jobs.ch/en/vacancies/?term={quote_plus(get_f('title', ''))}"

        serialized_jobs.append({
            "id": get_f('id'),
            "title": get_f('title', 'Unknown Title'),
            "company": get_f('company', 'Unknown Company'),
            "location": get_f('location', 'Unknown Location'),
            "job_type": get_f('job_type', 'Permanent'),
            "work_mode": get_f('work_mode', 'Hybrid'),
            "experience_level": get_f('experience_level', 'Mid-Senior Level'),
            "url": target_url,
            "score": (score if score is not None else 0) / 100.0,
            "is_verified": is_verified_match if is_verified_match is not None else get_f('is_verified', False),
            "verification_notes": get_f('validation_notes', ''),
            "skills_matched": skills_matched,
            "first_seen": get_f('first_seen_at', None).isoformat() if hasattr(get_f('first_seen_at'), 'isoformat') else None
        })
    
    print(f"DEBUG: Returning {len(serialized_jobs)} serialized jobs to frontend. LocFilter: {location_filter}, Total: {total}")
    return {
        "jobs": serialized_jobs,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    }

@app.post("/jobs/score")
async def trigger_job_scoring(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger alignment scoring for all existing jobs in the market.
    Matches jobs found in "Market Discovery" to the user's personal profile.
    """
    if JobFinderAgent is None:
        raise HTTPException(status_code=503, detail="Job Finder Agent not available")
        
    logger.info(f"User {current_user.id} triggered manual target scoring")
    
    try:
        agent = JobFinderAgent(db)
        result = await agent.personalize_market_jobs(current_user.id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
            
        return {
            "status": "success",
            "message": "Scoring completed successfully",
            "scored_count": result.get("matched_count", 0)
        }
    except Exception as e:
        logger.error(f"Error during manual scoring for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

# --- APPLICATION ENGINE ENDPOINTS ---

@app.get("/applications", response_model=List[JobApplicationResponse])
async def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all job applications for the current user."""
    apps = db.query(JobApplication).filter(JobApplication.user_id == current_user.id).all()
    
    # Manually populate virtual metadata fields for the response
    for app in apps:
        if app.job_opportunity:
            app.job_title = app.job_opportunity.title
            app.company_name = app.job_opportunity.company
            app.city = app.job_opportunity.location
            if not app.application_url:
                app.application_url = app.job_opportunity.application_url
    return apps

@app.get("/applications/{id}", response_model=JobApplicationResponse)
async def get_application(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single job application by ID."""
    application = db.query(JobApplication).filter(
        JobApplication.id == id,
        JobApplication.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job_opportunity:
        application.job_title = application.job_opportunity.title
        application.company_name = application.job_opportunity.company
        application.city = application.job_opportunity.location
        application.job_description = application.job_opportunity.description or ""
        if not application.application_url:
            application.application_url = application.job_opportunity.application_url
    return application

@app.post("/applications", response_model=JobApplicationResponse)
async def create_application(
    app_data: JobApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job application (from Job Finder, LinkedIn tab, or manual URL)."""
    # Resolve job_opportunity_id
    job_opp_id = app_data.job_opportunity_id

    if job_opp_id:
        if not db.query(JobOpportunity).filter(JobOpportunity.id == job_opp_id).first():
            raise HTTPException(status_code=404, detail="Job opportunity not found")

    # If a LinkedIn URL + title/company are supplied but no job_opportunity_id,
    # create a proper JobOpportunity so the tracker shows the real title.
    elif app_data.application_url and app_data.job_title and app_data.company_name:
        # Find or create a shared "LinkedIn" source row
        li_source = db.query(JobSource).filter(JobSource.name == "LinkedIn").first()
        if not li_source:
            li_source = JobSource(
                name="LinkedIn",
                url="https://www.linkedin.com/jobs/",
                source_type="standard_portal",
                country="Switzerland",
                is_active=True,
            )
            db.add(li_source)
            db.flush()

        # Avoid duplicate JobOpportunity for same URL
        existing_opp = db.query(JobOpportunity).filter(
            JobOpportunity.application_url == app_data.application_url
        ).first()
        if existing_opp:
            job_opp_id = existing_opp.id
        else:
            new_opp = JobOpportunity(
                source_id=li_source.id,
                title=app_data.job_title,
                company=app_data.company_name,
                location="Switzerland",
                application_url=app_data.application_url,
                is_live=True,
            )
            db.add(new_opp)
            db.flush()
            job_opp_id = new_opp.id

    # Check for existing application to avoid duplicates
    existing = db.query(JobApplication).filter(
        JobApplication.user_id == current_user.id,
        (JobApplication.job_opportunity_id == job_opp_id) if job_opp_id
        else (JobApplication.application_url == app_data.application_url)
    ).first()
    if existing:
        return existing

    application_url = app_data.application_url
    if not application_url and job_opp_id:
        opp = db.query(JobOpportunity).filter(JobOpportunity.id == job_opp_id).first()
        if opp:
            application_url = opp.application_url

    new_app = JobApplication(
        user_id=current_user.id,
        job_opportunity_id=job_opp_id,
        application_url=application_url,
        status=app_data.status or "draft",
        notes=app_data.notes,
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return new_app

class PrepareRequest(BaseModel):
    job_description: Optional[str] = None  # Optional: user-pasted job description override

@app.post("/applications/{id}/prepare")
async def prepare_application_materials(
    id: int,
    body: Optional[PrepareRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger AI to tailor CV and Cover Letter for this application."""
    if JobPreparationAgent is None:
        raise HTTPException(status_code=503, detail="Job Preparation Agent not available")

    application = db.query(JobApplication).filter(JobApplication.id == id, JobApplication.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # If the user pasted a job description, store it on the linked job opportunity
    pasted_desc = (body.job_description or "").strip() if body else ""
    if pasted_desc and application.job_opportunity_id:
        job = db.query(JobOpportunity).filter(JobOpportunity.id == application.job_opportunity_id).first()
        if job:
            job.description = pasted_desc
            db.commit()

    agent = JobPreparationAgent(db)
    result = await agent.prepare_application(
        current_user.id, application.id,
        job_description_override=pasted_desc or None
    )

    if result["status"] == "error":
        # "description_required" is a user-actionable error (not a server fault) — use 422
        if result.get("error_code") == "description_required":
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "description_required",
                    "scrape_status": result.get("scrape_status", "unknown"),
                    "message": result["message"],
                    "url": result.get("url"),
                },
            )
        raise HTTPException(status_code=500, detail=result["message"])

    return result

@app.post("/applications/{id}/apply")
async def apply_to_job_automated(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger the Auto-Apply Agent."""
    if AutoApplyAgent is None:
        raise HTTPException(status_code=503, detail="Auto Apply Agent not available")
        
    application = db.query(JobApplication).filter(JobApplication.id == id, JobApplication.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Guard: prevent spawning a second browser if automation is already running
    if application.status == "applying":
        raise HTTPException(status_code=409, detail="Auto-apply is already running for this application. Please wait for it to complete or check the browser window.")

    # Validation: Ensure materials are prepared
    if not application.tailored_cv or not application.cover_letter:
        raise HTTPException(status_code=400, detail="Materials must be prepared before auto-apply. Please click 'Prep' first.")

    # Validation: Ensure there is a URL to apply to
    url = application.application_url
    if not url and application.job_opportunity_id:
        from app.models.database import JobOpportunity as _JO
        job = db.query(_JO).filter(_JO.id == application.job_opportunity_id).first()
        if job:
            url = job.application_url
    if not url:
        raise HTTPException(status_code=400, detail="No application URL found for this job. Please add a job link before running Auto-Apply.")

    agent = AutoApplyAgent(db)
    try:
        result = await agent.run_automation(id)
    except Exception as e:
        logger.exception(f"Auto-apply agent crashed for application {id}")
        raise HTTPException(status_code=500, detail=f"Auto-apply error: {str(e)}")

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result

@app.patch("/applications/{id}", response_model=JobApplicationResponse)
async def update_application(
    id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update application status, notes, or content."""
    application = db.query(JobApplication).filter(JobApplication.id == id, JobApplication.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    # Check if content-related fields are being updated to trigger PDF regeneration
    content_changed = "tailored_cv" in updates or "cover_letter" in updates
    
    for key, value in updates.items():
        if hasattr(application, key):
            setattr(application, key, value)
            
    db.commit()
    
    # If content changed, regenerate high-fidelity PDFs in background (or sync if we want immediate update)
    if content_changed and JobPreparationAgent:
        try:
            agent = JobPreparationAgent(db)
            # We use the potentially updated values from the database or the updates dict
            cv_text = updates.get("tailored_cv", application.tailored_cv)
            cl_text = updates.get("cover_letter", application.cover_letter)
            
            # This is relatively fast (LLM + Playwright), but for best UX we do it here
            # so the user gets the new paths in the response if they want to download immediately
            await agent.regenerate_pdfs_from_text(current_user.id, id, cv_text, cl_text)
        except Exception as e:
            logger.error(f"Error regenerating PDFs during update: {e}")
            
    db.refresh(application)
    
    # Manually populate virtual fields for response
    if application.job_opportunity:
        application.job_title = application.job_opportunity.title
        application.company_name = application.job_opportunity.company
        application.city = application.job_opportunity.location
        if not application.application_url:
            application.application_url = application.job_opportunity.application_url
            
    return application

@app.delete("/applications/{id}")
async def delete_application(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an application entry."""
    application = db.query(JobApplication).filter(JobApplication.id == id, JobApplication.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    db.delete(application)
    db.commit()
    return {"status": "success", "message": "Application deleted"}

@app.get("/social/analysis")
async def get_social_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy stub — kept for backwards compatibility."""
    return {"status": "ok", "message": "Use /social/topics and /social/content endpoints"}


# ═══════════════════════════════════════════════════════════════════════════
# SOCIAL VISIBILITY — Topics
# ═══════════════════════════════════════════════════════════════════════════

try:
    from agents.social_content_agent import SocialContentAgent
except ImportError:
    SocialContentAgent = None  # type: ignore


class SocialTopicCreate(BaseModel):
    title: str
    summary: Optional[str] = ""


class SocialContentGenerateRequest(BaseModel):
    topic_id: Optional[int] = None
    custom_topic: Optional[str] = None
    content_type: str = "article"    # article | post | thread
    platform: str = "linkedin"       # linkedin | twitter | medium | github
    tone: str = "thought_leader"     # thought_leader | conversational | professional | storytelling


class SocialContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    hook_a: Optional[str] = None
    hook_b: Optional[str] = None
    hashtags: Optional[list] = None
    status: Optional[str] = None
    scheduled_at: Optional[str] = None
    published_at: Optional[str] = None
    published_url: Optional[str] = None
    engagement_notes: Optional[str] = None


@app.get("/social/dashboard")
async def get_social_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Visibility score, posting stats, and content breakdown."""
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    return agent.get_dashboard(current_user.id)


@app.get("/social/topics")
async def list_social_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all topic ideas (AI-suggested + user-provided)."""
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    return {"topics": agent.list_topics(current_user.id)}


@app.post("/social/topics/suggest")
async def suggest_social_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask the AI to generate 10 topic ideas from the user's profile."""
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    topics = await agent.suggest_topics(current_user.id, count=10)
    return {"topics": topics}


@app.post("/social/topics")
async def create_social_topic(
    body: SocialTopicCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a user-provided topic."""
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    topic = await agent.save_user_topic(current_user.id, body.title, body.summary)
    return topic


@app.delete("/social/topics/{topic_id}")
async def delete_social_topic(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    if not agent.delete_topic(current_user.id, topic_id):
        raise HTTPException(status_code=404, detail="Topic not found")
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════════
# SOCIAL VISIBILITY — Content pieces
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/social/content/generate")
async def generate_social_content(
    body: SocialContentGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new article, post, or thread via AI."""
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    if not body.topic_id and not body.custom_topic:
        raise HTTPException(status_code=400, detail="Provide either topic_id or custom_topic")
    agent = SocialContentAgent(db)
    result = await agent.generate_content(
        user_id=current_user.id,
        topic_id=body.topic_id,
        custom_topic=body.custom_topic,
        content_type=body.content_type,
        platform=body.platform,
        tone=body.tone,
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.get("/social/content")
async def list_social_content(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    content_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all content pieces, optionally filtered."""
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    return {"content": agent.list_content(current_user.id, status, platform, content_type)}


@app.get("/social/content/{piece_id}")
async def get_social_content(
    piece_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    piece = agent.get_content(current_user.id, piece_id)
    if not piece:
        raise HTTPException(status_code=404, detail="Content piece not found")
    return piece


@app.put("/social/content/{piece_id}")
async def update_social_content(
    piece_id: int,
    body: SocialContentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    piece = agent.update_content(current_user.id, piece_id, updates)
    if not piece:
        raise HTTPException(status_code=404, detail="Content piece not found")
    return piece


@app.delete("/social/content/{piece_id}")
async def delete_social_content(
    piece_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if SocialContentAgent is None:
        raise HTTPException(status_code=503, detail="SocialContentAgent not available")
    agent = SocialContentAgent(db)
    if not agent.delete_content(current_user.id, piece_id):
        raise HTTPException(status_code=404, detail="Content piece not found")
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════════
# LINKEDIN PROFILE AUDIT  (standalone — placement TBD)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/social/linkedin/audit")
async def run_linkedin_audit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stub — full LinkedIn Profile Audit agent coming as separate feature."""
    raise HTTPException(
        status_code=501,
        detail="LinkedIn Profile Audit is being built as a standalone feature. Coming soon."
    )


@app.get("/social/linkedin/audit/latest")
async def get_latest_linkedin_audit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the most recent audit for this user, if any."""
    from app.models.database import LinkedInProfileAudit
    audit = db.query(LinkedInProfileAudit).filter(
        LinkedInProfileAudit.user_id == current_user.id
    ).order_by(LinkedInProfileAudit.audited_at.desc()).first()
    if not audit:
        return {"audit": None}
    return {"audit": {
        "id": audit.id,
        "audited_at": audit.audited_at.isoformat(),
        "overall_score": audit.overall_score,
        "completeness_score": audit.completeness_score,
        "visibility_score": audit.visibility_score,
        "headline_current": audit.headline_current,
        "headline_suggested": audit.headline_suggested,
        "gaps": audit.gaps,
        "action_items": audit.action_items,
    }}

@app.get("/social/platforms")
async def get_social_platforms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's social platform configurations."""
    from app.models.database import UserSocialPlatformConfig
    configs = db.query(UserSocialPlatformConfig).filter(
        UserSocialPlatformConfig.user_id == current_user.id
    ).all()
    return {"platforms": [
        {
            "platform": c.platform,
            "enabled": c.enabled,
            "automation_type": c.automation_type,
            "platform_handle": c.platform_handle,
            "platform_url": c.platform_url,
        } for c in configs
    ]}


@app.post("/social/platforms")
async def save_social_platforms(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upsert social platform configurations for the user."""
    from app.models.database import UserSocialPlatformConfig
    platforms = payload.get("platforms", [])
    for entry in platforms:
        p = entry.get("platform")
        if not p:
            continue
        existing = db.query(UserSocialPlatformConfig).filter(
            UserSocialPlatformConfig.user_id == current_user.id,
            UserSocialPlatformConfig.platform == p,
        ).first()
        if existing:
            existing.enabled = entry.get("enabled", existing.enabled)
            existing.automation_type = entry.get("automation_type", existing.automation_type)
            existing.platform_handle = entry.get("platform_handle", existing.platform_handle)
            existing.platform_url = entry.get("platform_url", existing.platform_url)
        else:
            db.add(UserSocialPlatformConfig(
                user_id=current_user.id,
                platform=p,
                enabled=entry.get("enabled", False),
                automation_type=entry.get("automation_type", "none"),
                platform_handle=entry.get("platform_handle"),
                platform_url=entry.get("platform_url"),
            ))
    db.commit()
    return {"status": "saved"}

# --- END SOCIAL VISIBILITY ENDPOINTS ---

# ═══════════════════════════════════════════════════════════════════════════
# AUTO-APPLY SETTINGS & ACCOUNT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

from app.models.database import AutoApplyCredential, AutoApplyAccount
from app.models.schemas import (
    AutoApplySettingsRequest, AutoApplySettingsResponse,
    AutoApplyAccountCreate, AutoApplyAccountResponse,
    InterventionRequest,
)
from app.utils.security import encrypt_value, decrypt_value, mask_password


@app.get("/auto-apply/settings", response_model=AutoApplySettingsResponse)
async def get_auto_apply_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch auto-apply credential configuration (passwords masked)."""
    creds = db.query(AutoApplyCredential).filter(
        AutoApplyCredential.user_id == current_user.id
    ).first()

    if not creds:
        return AutoApplySettingsResponse(configured=False)

    return AutoApplySettingsResponse(
        configured=True,
        linkedin_url=creds.linkedin_url,
        linkedin_username=creds.linkedin_username,
        linkedin_password_set=bool(creds.linkedin_password_enc),
        email_username=creds.email_username,
        email_password_set=bool(creds.email_password_enc),
        llm_provider=creds.llm_provider or "gemini",
    )


@app.post("/auto-apply/settings", response_model=AutoApplySettingsResponse)
async def save_auto_apply_settings(
    payload: AutoApplySettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save/update auto-apply credentials. Passwords are encrypted before storage."""
    creds = db.query(AutoApplyCredential).filter(
        AutoApplyCredential.user_id == current_user.id
    ).first()

    if not creds:
        creds = AutoApplyCredential(user_id=current_user.id)
        db.add(creds)

    if payload.linkedin_url is not None:
        creds.linkedin_url = payload.linkedin_url
    if payload.linkedin_username is not None:
        creds.linkedin_username = payload.linkedin_username
    if payload.linkedin_password is not None:
        creds.linkedin_password_enc = encrypt_value(payload.linkedin_password) if payload.linkedin_password else ""
    if payload.email_username is not None:
        creds.email_username = payload.email_username
    if payload.email_password is not None:
        creds.email_password_enc = encrypt_value(payload.email_password) if payload.email_password else ""
    if payload.llm_provider is not None and payload.llm_provider in ("gemini", "claude"):
        creds.llm_provider = payload.llm_provider

    creds.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(creds)

    return AutoApplySettingsResponse(
        configured=True,
        linkedin_url=creds.linkedin_url,
        linkedin_username=creds.linkedin_username,
        linkedin_password_set=bool(creds.linkedin_password_enc),
        email_username=creds.email_username,
        email_password_set=bool(creds.email_password_enc),
        llm_provider=creds.llm_provider or "gemini",
    )


@app.get("/auto-apply/accounts", response_model=List[AutoApplyAccountResponse])
async def get_auto_apply_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all portal accounts created during automation for this user."""
    accounts = db.query(AutoApplyAccount).filter(
        AutoApplyAccount.user_id == current_user.id
    ).order_by(AutoApplyAccount.created_at.desc()).all()
    return accounts


@app.post("/auto-apply/accounts", response_model=AutoApplyAccountResponse)
async def add_auto_apply_account(
    payload: AutoApplyAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually log a portal account."""
    account = AutoApplyAccount(
        user_id=current_user.id,
        application_id=payload.application_id,
        platform_name=payload.platform_name,
        platform_url=payload.platform_url,
        username=payload.username,
        password=payload.password,
        notes=payload.notes,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@app.get("/applications/{id}/status")
async def get_application_status(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lightweight polling endpoint: returns current status, intervention_message,
    and last 20 log lines for a live auto-apply progress display.
    """
    application = db.query(JobApplication).filter(
        JobApplication.id == id,
        JobApplication.user_id == current_user.id,
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    log_lines = []
    try:
        import json as _json
        log_lines = _json.loads(application.auto_apply_log or "[]")[-20:]
    except Exception:
        pass

    return {
        "id": id,
        "status": application.status,
        "intervention_message": application.intervention_message,
        "log": log_lines,
    }


@app.post("/applications/{id}/intervention")
async def handle_intervention(
    id: int,
    payload: InterventionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Receives user response to an automation blocker.
    Stores the response data so the agent can read it and resume.
    """
    application = db.query(JobApplication).filter(
        JobApplication.id == id,
        JobApplication.user_id == current_user.id,
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if payload.action == "abort":
        application.status = "draft"
        application.intervention_message = "Automation aborted by user."
    else:
        # Store the intervention data for the agent to pick up, reset status
        application.auto_apply_intervention_data = payload.intervention_data or ""
        application.status = "applying"
        application.intervention_message = None

    import json as _json
    existing = _json.loads(application.auto_apply_log or "[]")
    action_msg = f"User action: {payload.action}" + (f" — {payload.intervention_data}" if payload.intervention_data else "")
    existing.append(action_msg)
    application.auto_apply_log = _json.dumps(existing[-50:])

    db.commit()

    return {
        "status": "ok",
        "application_status": application.status,
        "message": f"Intervention processed: {payload.action}",
    }


# ═══════════════════════════════════════════════════════════════════════════

# Mount uploads directory to serve files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve frontend at root as well
frontend_dir = os.path.join(os.getcwd(), 'simple_frontend')
if os.path.exists(frontend_dir):
    app.mount('/', StaticFiles(directory=frontend_dir, html=True), name='frontend')


if __name__ == '__main__':
    import uvicorn
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run("app.main:app", host="0.0.0.0", port=8005, reload=True)
