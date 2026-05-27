import base64
import logging
import json
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.database import JobOpportunity, JobApplication, User, UserProfile, UserExperience, UserSkill, UserEducation
from app.services.llm_analysis import LLMAnalysisService
from app.services.extraction_service import ExtractionService
from app.services.pdf_service import PDFService
from app.services.linkedin_browser import LinkedInBrowserService
from PIL import Image
import io

logger = logging.getLogger(__name__)

class JobPreparationAgent:
    """Agent for preparing job application materials."""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMAnalysisService()
        self.extractor = ExtractionService()
        self.pdf_service = PDFService()

    def _get_image_data_uri(self, file_path: str) -> Optional[str]:
        """Convert a local image file to a Base64 data URI."""
        if not file_path:
            return None
            
        try:
            # Normalize path: remove leading slash and ensure it exists relative to current dir
            clean_path = file_path.lstrip('/')
            abs_path = os.path.abspath(clean_path)
            
            if not os.path.exists(abs_path):
                logger.error(f"Image file not found at: {abs_path}")
                return None
            
            ext = os.path.splitext(abs_path)[1].lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            
            with open(abs_path, "rb") as image_file:
                # Resize image if it's too large to prevent Playwright timeouts
                img = Image.open(image_file)
                
                # Max dimensions for CV photo (300x300 is plenty for high fidelity)
                max_size = (400, 400)
                if img.width > max_size[0] or img.height > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Save back to bytes
                    img_byte_arr = io.BytesIO()
                    # Use original format if possible, otherwise JPEG
                    save_format = img.format if img.format else 'JPEG'
                    img.save(img_byte_arr, format=save_format, quality=85)
                    encoded_string = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                else:
                    # Small enough, use original
                    image_file.seek(0)
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
                return f"data:image/{ext};base64,{encoded_string}"
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            return None

    def _normalize_experience_dates(self, experiences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Strip month/day info from experience dates, keeping year only (e.g. '2025-01' -> '2025')."""
        def year_only(date_str: str) -> str:
            if not date_str:
                return date_str
            # Replace "YYYY-MM" or "YYYY/MM" with just "YYYY"
            cleaned = re.sub(r'(\d{4})[-/]\d{2}', r'\1', date_str)
            # Replace "Jan 2025" / "January 2025" style
            cleaned = re.sub(r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})', r'\1', cleaned, flags=re.IGNORECASE)
            return cleaned.strip()

        normalized = []
        for exp in experiences:
            exp_copy = dict(exp)
            if 'dates' in exp_copy:
                exp_copy['dates'] = year_only(exp_copy['dates'])
            normalized.append(exp_copy)
        return normalized

    def _generate_markdown_cv(self, context: Dict[str, Any]) -> str:
        """Convert structured CV context into a clean Markdown string for editing."""
        md = f"# {context.get('name', 'N/A')}\n"
        md += f"{context.get('tagline', 'N/A')}\n\n"
        
        md += "## CONTACT\n"
        md += f"- Location: {context.get('location', 'N/A')}\n"
        md += f"- Phone: {context.get('phone', 'N/A')}\n"
        md += f"- Email: {context.get('email', 'N/A')}\n"
        if context.get('linkedin_url'):
            md += f"- LinkedIn: {context['linkedin_url']}\n"
        md += "\n"
        
        md += "## PERSONAL\n"
        md += f"- Date of Birth: {context.get('dob', 'N/A')}\n"
        md += f"- Nationality: {context.get('nationality', 'N/A')}\n"
        md += f"- Marital Status: {context.get('marital_status', 'N/A')}\n"
        md += f"- Work Authorization: {context.get('work_auth', 'N/A')}\n\n"
        
        md += "## EXPERTISE\n"
        md += f"{context.get('expertise_summary', 'N/A')}\n\n"
        
        md += "## PROFESSIONAL EXPERIENCE\n"
        for exp in context.get('experiences', []):
            md += f"### {exp.get('role', 'Position')} | {exp.get('company', 'Company')} | {exp.get('dates', 'Dates')}\n"
            for bullet in exp.get('bullets', []):
                md += f"- {bullet}\n"
            md += "\n"
            
        md += "## EDUCATION\n"
        for edu in context.get('education', []):
            md += f"### {edu.get('degree', 'Degree')} | {edu.get('institution', 'Institution')} | {edu.get('year', '')}\n"
        md += "\n"
        
        md += "## LANGUAGES\n"
        for lang in context.get('languages', []):
            md += f"- {lang.get('name', 'Language')} (Level: {lang.get('level', '3')}/5)\n"
        md += "\n"
        
        md += "## IT SKILLS\n"
        md += ", ".join(context.get('it_skills', [])) + "\n\n"
        
        md += "## CERTIFICATIONS\n"
        for cert in context.get('certifications', []):
            md += f"- {cert}\n"
        md += "\n"
        
        md += "## SKILLS / STRENGTHS\n"
        for strength in context.get('strengths', []):
            md += f"- {strength}\n"
            
        return md

    async def _analyze_job(self, job_description: str) -> Dict[str, Any]:
        """Phase 1: The Analyzer Agent (The Strategist)."""
        prompt = f"""
        Act as a Strategic Recruitment Consultant and ATS Optimizer. Distill the following job description into a 'Battle Plan'.
        
        JOB DESCRIPTION:
        {job_description[:5000]}
        
        OUTPUT REQUIREMENTS:
        1. **top_skills**: List the 5 most critical 'Must-Have' technical or soft skills.
        2. **company_voice**: Identify the tone of the company (e.g., Innovative Startup, Blue Chip Corporate, Academic/Research, Modern Tech).
        3. **keywords**: Extract 10-15 high-impact keywords/entities (tools, certifications, methodologies) for ATS optimization.
        4. **highlight_achievements**: Based on the requirements, what 3 types of achievements should the candidate prioritize?
        
        Return ONLY a valid JSON object with keys: 'top_skills', 'company_voice', 'keywords', 'highlight_achievements'.
        """
        return await self.llm.generate_json(prompt)

    async def _audit_content(self, job_description: str, cv_text: str, cl_text: str, target_keywords: List[str] = None) -> Dict[str, Any]:
        """Phase 3: The Critic Agent (The 'Auto-Reviewer')."""
        prompt = f"""
        Act as a Senior Recruiter and ATS Auditor. Audit the tailored CV and Cover Letter against the Job Description.
        
        TARGET KEYWORDS: {target_keywords or []}
        JOB DESCRIPTION: {job_description[:2000]}
        TAILORED CV (Markdown): {cv_text[:2000]}
        COVER LETTER: {cl_text[:1500]}
        
        CRITERIA:
        1. **score**: 1-10.
        2. **feedback**: Specific improvements.
        3. **scannability**: Does the cover letter use a 3-part structure with 3-4 bullet points for achievements? (Score < 5 and is_approved = False if it lacks '-' markdown bullets).
        4. **hallucination_check**: List any claims/metrics not in the Master Data. (is_approved = False if any).
        5. **keyword_saturation**: What % of target keywords were used?
        6. **is_approved**: True ONLY if score >= 8 AND hallucination_check passed AND scannability is high.
        
        Return ONLY a valid JSON object with keys: 'score', 'feedback', 'is_approved', 'hallucination_check', 'keyword_saturation'.
        """
        return await self.llm.generate_json(prompt)

    async def _refine_content(self, master_context: Dict[str, Any], current_tailored_data: Dict[str, Any], feedback: str) -> Dict[str, Any]:
        """Phase 4: Refinement loop based on Critic feedback."""
        prompt = f"""
        Act as an Executive Writer. Refine the tailored CV/CL content based on the following recruiter feedback.
        
        FEEDBACK:
        {feedback}
        
        CURRENT TAILED DATA (JSON):
        {json.dumps(current_tailored_data, indent=2)}
        
        USER MASTER DATA:
        {json.dumps(master_context['user'], indent=2)}
        
        REQUIREMENTS:
        - Address the feedback precisely.
        - Maintain strict alignment with the USER MASTER DATA (no hallucinations).
        - Keep the professional tone.
        
        Return the result ONLY as a valid JSON object with keys: 'tagline', 'expertise_summary', 'tailored_experiences', 'tailored_strengths', 'cover_letter'.
        """
        return await self.llm.generate_json(prompt)

    async def prepare_application(self, user_id: int, application_id: int, job_description_override: Optional[str] = None) -> Dict[str, Any]:
        """
        1. Fetch application and related job/user data.
        2. If job description is missing (manual URL), scrape it.
        3. Phase 1-4: Multi-agent Analyze-Write-Audit-Refine pipeline.
        4. Render to high-fidelity PDF using Playwright.
        """
        app = self.db.query(JobApplication).filter(JobApplication.id == application_id).first()
        if not app:
            raise ValueError("Application not found")

        logger.info(f"PREPARE: application_id={application_id}, url={app.application_url}, job_opp_id={app.job_opportunity_id}")

        user = self.db.query(User).filter(User.id == user_id).first()
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        job_title = "Position"
        company = "Company"
        job_description = "No description provided"

        # User-pasted override takes highest priority
        if job_description_override:
            job_description = job_description_override
            logger.info("Using user-provided job description override.")

        if app.job_opportunity_id:
            job = self.db.query(JobOpportunity).filter(JobOpportunity.id == app.job_opportunity_id).first()
            if job:
                job_title = job.title
                company = job.company
                # Use DB description only if no override was given
                if not job_description_override:
                    job_description = job.description or ""
        
        # If still no description, try to scrape from the application URL
        needs_description = not job_description or job_description in (
            "No description provided", "No description available — please ensure the job description is stored."
        ) or len(job_description.strip()) < 150

        if needs_description and app.application_url:
            raw_url = app.application_url

            # ── LinkedIn: attempt authenticated scrape if connected ──────────
            if "linkedin.com" in raw_url.lower():
                li_browser = LinkedInBrowserService()
                status = li_browser.session_status(self.db, user_id)
                
                if status.get("connected"):
                    logger.info(f"[LinkedIn] Attempting authenticated JD fetch for user {user_id}")
                    fetched_desc = await li_browser.fetch_job_description(self.db, user_id, raw_url)
                    if fetched_desc:
                        job_description = fetched_desc
                        needs_description = False
                        logger.info(f"[LinkedIn] Successfully retrieved JD via browser session")
                        # Persist so reprepare doesn't re-scrape every time
                        if app.job_opportunity_id:
                            _jobj = self.db.query(JobOpportunity).filter(
                                JobOpportunity.id == app.job_opportunity_id
                            ).first()
                            if _jobj:
                                _jobj.description = fetched_desc
                                self.db.commit()
                
                if needs_description:
                    # Extract job ID and build a clean canonical URL for the user to open
                    m = re.search(r'/jobs/view/(\d+)', raw_url)
                    if not m:
                        m = re.search(r'[?&]currentJobId=(\d+)', raw_url)
                    job_id = m.group(1) if m else None
                    canonical = f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else raw_url.split('?')[0]
                    msg = (
                        "LinkedIn job descriptions require you to be logged in — they cannot be accessed automatically. "
                        "Please connect your LinkedIn account or paste the description manually."
                    )
                    if status.get("connected"):
                        msg = (
                            "We tried to fetch the LinkedIn job description automatically, but LinkedIn blocked the request or the content was hidden. "
                            "Please open the job posting manually, copy the full description, and paste it below."
                        )
                    
                    return {
                        "status": "error",
                        "error_code": "description_required",
                        "scrape_status": "auth_required" if not status.get("connected") else "not_found",
                        "message": msg,
                        "url": canonical,
                    }
            else:
                # ── Other URLs: attempt scraping with diagnosis ───────────────────
                diagnosis = await self.extractor.extract_with_diagnosis(raw_url)
                if diagnosis["status"] == "success":
                    job_description = diagnosis["content"]
                    logger.info(f"Scraped job description ({len(job_description)} chars) from {raw_url}")
                else:
                    logger.warning(f"Job description unavailable: [{diagnosis['status']}] {diagnosis['reason']}")
                    return {
                        "status": "error",
                        "error_code": "description_required",
                        "scrape_status": diagnosis["status"],
                        "message": diagnosis["reason"],
                        "url": raw_url,
                    }

        elif needs_description and not app.application_url:
            return {
                "status": "error",
                "error_code": "description_required",
                "scrape_status": "no_url",
                "message": (
                    "No job URL is set and no description was pasted. "
                    "Please paste the full job description in the field below before generating your materials."
                ),
                "url": None,
            }

        # Gather formal master context
        experiences = self.db.query(UserExperience).filter(UserExperience.user_id == user_id).all()
        skills = self.db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
        education = self.db.query(UserEducation).filter(UserEducation.user_id == user_id).all()
        
        # Prepare context for LLM tailoring
        # TOKEN GUARD: Truncate job description to 2500 characters for high-fidelity focus
        truncated_desc = job_description[:2500] if job_description else ""
        
        master_context = {
            "job": {"title": job_title, "company": company, "description": truncated_desc},
            "user": {
                "name": user.full_name,
                "summary": profile.summary if profile else "",
                "skills": [s.skill_name for s in skills if s.category == 'technical'],
                "experience": [
                    {
                        "role": e.position,
                        "company": e.company,
                        "dates": f"{e.start_date.strftime('%Y')} - {e.end_date.strftime('%Y') if e.end_date else 'Present'}",
                        "bullets": e.description.split('\n') if e.description else []
                    } for e in experiences
                ],
                "strengths": [s.skill_name for s in skills if s.category == 'soft']
            }
        }

        # --- PHASE 1: ANALYZE ---
        battle_plan = await self._analyze_job(job_description)
        logger.info(f"Battle Plan generated: {json.dumps(battle_plan, indent=2)}")

        # --- PHASE 2: WRITE ---
        # Refined prompt for the Writer Agent incorporating the 3-part bulleted Cover Letter
        prompt = f"""
        Act as an Executive Writer executing a Strategic Battle Plan.
        
        BATTLE PLAN:
        {json.dumps(battle_plan, indent=2)}
        
        USER MASTER DATA:
        {json.dumps(master_context['user'], indent=2)}
        
        NEGATIVE CONSTRAINTS:
        - Do NOT use flowery language like 'passionate professional' or 'proven track record'.
        - Do NOT mention skills, tools, or metrics the user does NOT explicitly have in the USER DATA.
        - Focus on ACTION and QUANTIFIABLE results found in the USER DATA.
        
        REQUIREMENTS:
        1. **tagline**: One-line punchy subtitle aligned with {battle_plan.get('company_voice', 'Modern Business')}.
        2. **expertise_summary**: Professional summary prioritizing the top skills identified: {battle_plan.get('top_skills', [])}.
        3. **tailored_experiences**: List of experiences with rewritten bullets focused on: {battle_plan.get('highlight_achievements', [])}. Each experience must include 'role', 'company', 'dates' (year only, e.g. "2025 - Present" or "2023 - 2025"), and 'bullets'.
        4. **tailored_strengths**: List of 10-12 strengths aligned with the job.
        5. **cover_letter**: A formal, highly scannable cover letter (MAX 350 words) with this structure:
           - PART 1: Opening stating why the candidate is a perfect fit for {job_title}.
           - PART 2: 3-4 high-impact BULLET POINTS demonstrating quantifiable achievements from USER DATA that solve core job challenges.
             YOU MUST use the format:
             - Achieved [Metric] by [Action]
             - Reduced [Cost/Time] via [Strategy]
           - PART 3: Motivation (alignment with {battle_plan.get('company_voice', 'the company')}) and a clear 'ask' for an interview.
        
        Return JSON object: 'tagline', 'expertise_summary', 'tailored_experiences', 'tailored_strengths', 'cover_letter'.
        """

        try:
            response_data = await self.llm.generate_json(prompt)
            if "error" in response_data:
                raise ValueError(f"LLM Error: {response_data['error']}")

            # Normalize experience dates to year-only (e.g. "2025-01" -> "2025")
            if 'tailored_experiences' in response_data:
                response_data['tailored_experiences'] = self._normalize_experience_dates(response_data['tailored_experiences'])

            # --- PHASE 3 & 4: AUDIT & REFINEMENT LOOP ---
            max_attempts = 2
            attempt = 0
            is_approved = False
            
            while attempt < max_attempts and not is_approved:
                attempt += 1
                
                # Check Length Guard first
                cl_text = response_data.get('cover_letter', '')
                word_count = len(cl_text.split())
                if word_count > 350:
                    logger.warning(f"Length Guard Triggered: {word_count} words. Requesting reduction.")
                    response_data = await self._refine_content(
                        master_context, 
                        response_data, 
                        f"CRITICAL: The cover letter is too long ({word_count} words). Reduce to under 300 words while keeping the 3-part bulleted structure."
                    )
                    continue

                # Generate temporary markdown for audit
                temp_cv_context = {
                    "name": user.full_name,
                    "tagline": response_data.get('tagline', ''),
                    "expertise_summary": response_data.get('expertise_summary', ''),
                    "experiences": response_data.get('tailored_experiences', []),
                    "strengths": response_data.get('tailored_strengths', [])
                }
                temp_md_cv = self._generate_markdown_cv(temp_cv_context)
                
                audit = await self._audit_content(
                    job_description, 
                    temp_md_cv, 
                    cl_text, 
                    target_keywords=battle_plan.get('keywords', [])
                )
                
                is_approved = audit.get('is_approved', False)
                
                # FINAL FAIL-SAFE: If no bullets found in text, force rejection regardless of score
                if '-' not in cl_text and '*' not in cl_text:
                    logger.warning("Fail-Safe: No bullets found in cover letter. Forcing refinement.")
                    is_approved = False
                    audit['feedback'] = "The cover letter is missing bullet points. You MUST use markdown bullets (e.g., - Achievement) for the middle section."

                logger.info(f"Audit Attempt {attempt}: Score {audit.get('score')}/10 - Approved: {is_approved}")
                
                if not is_approved and attempt < max_attempts:
                    logger.info(f"Refinement triggered: {audit.get('feedback')}")
                    response_data = await self._refine_content(master_context, response_data, audit.get('feedback', 'Improve depth.'))
                    if 'tailored_experiences' in response_data:
                        response_data['tailored_experiences'] = self._normalize_experience_dates(response_data['tailored_experiences'])

            # 4. Prepare Context for PDF Template
            # Map proficiency to dots
            prof_map = {
                "beginner": 1,
                "limited": 1,
                "intermediate": 2,
                "professional": 3,
                "advanced": 3,
                "fluent": 4,
                "native": 5,
                "expert": 5
            }
            
            cv_context = {
                "name": user.full_name,
                "tagline": response_data.get('tagline', 'Professional'),
                "expertise_summary": response_data.get('expertise_summary', profile.summary),
                "experiences": response_data.get('tailored_experiences', master_context['user']['experience']),
                "education": [
                    {
                        "year": edu.end_date.strftime("%Y") if edu.end_date else "",
                        "degree": edu.degree,
                        "institution": edu.institution
                    } for edu in education
                ],
                "location": profile.location or "N/A",
                "phone": profile.phone or "N/A",
                "email": user.email,
                "linkedin_url": profile.linkedin_url or "",
                "profile_picture_url": self._get_image_data_uri(profile.profile_picture_url),
                "dob": profile.dob or "N/A",
                "nationality": profile.nationality or "N/A",
                "marital_status": profile.marital_status or "N/A",
                "work_auth": profile.work_auth or "N/A",
                "languages": [
                    {"name": s.skill_name, "level": prof_map.get((s.proficiency or "intermediate").lower(), 3)}
                    for s in skills if s.category == 'language'
                ],
                "it_skills": [s.skill_name for s in skills if s.category == 'technical'],
                "certifications": [s.skill_name for s in skills if s.category == 'certification'],
                "strengths": response_data.get('tailored_strengths', master_context['user']['strengths'])
            }

            # Generate Markdown Version for Editor
            markdown_cv = self._generate_markdown_cv(cv_context)

            # 5. Generate PDFs
            upload_dir = os.path.join("uploads", str(user_id), "applications", str(application_id))
            os.makedirs(upload_dir, exist_ok=True)
            
            cv_filename = f"Tailored_CV_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            cl_filename = f"Cover_Letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            cv_path = os.path.join(upload_dir, cv_filename)
            cl_path = os.path.join(upload_dir, cl_filename)
            
            cl_context = {
                "name": user.full_name,
                "location": profile.location or "",
                "phone": profile.phone or "",
                "email": user.email,
                "company": company,
                "job_title": job_title,
                "content": response_data.get('cover_letter', ''),
                "date": datetime.now().strftime("%B %d, %Y")
            }

            cv_success = await self.pdf_service.create_cv_pdf(cv_context, cv_path)
            cl_success = await self.pdf_service.create_cl_pdf(cl_context, cl_path)

            if not cv_success or not cl_success:
                logger.warning("PDF generation partially failed.")

            # 6. Update Database
            app.tailored_cv = markdown_cv  # Store full markdown CV
            app.cover_letter = response_data.get('cover_letter', '')
            app.cv_path = cv_path if cv_success else None
            app.cl_path = cl_path if cl_success else None
            app.status = 'prepared'
            app.generated_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "status": "success",
                "job_title": job_title,
                "company": company,
                "tailored_cv": app.tailored_cv,
                "cover_letter": app.cover_letter,
                "cv_path": app.cv_path,
                "cl_path": app.cl_path
            }
            
        except Exception as e:
            logger.error(f"Error in JobPreparationAgent: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}

    async def regenerate_pdfs_from_text(self, user_id: int, application_id: int, cv_text: str, cl_text: str) -> Dict[str, Any]:
        """Parse edited Markdown back to JSON and regenerate PDFs."""
        app = self.db.query(JobApplication).filter(JobApplication.id == application_id).first()
        if not app:
            raise ValueError("Application not found")
            
        user = self.db.query(User).filter(User.id == user_id).first()
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        job_title = "Position"
        company = "Company"
        if app.job_opportunity:
            job_title = app.job_opportunity.title
            company = app.job_opportunity.company

        # Prompt LLM to structure the edited Markdown back into JSON for the template
        parse_prompt = f"""
        Extract structured CV data from the following Markdown CV. 
        Return ONLY a JSON object compatible with the modern CV template.
        
        MARKDOWN CV:
        {cv_text}
        
        REQUIRED JSON SCHEMA:
        {{
          "tagline": "string",
          "expertise_summary": "string",
          "experiences": [{{ "role": "string", "company": "string", "dates": "string", "bullets": ["string"] }}],
          "education": [{{ "year": "string", "degree": "string", "institution": "string" }}],
          "location": "string",
          "phone": "string",
          "email": "string",
          "linkedin_url": "string",
          "dob": "string",
          "nationality": "string",
          "marital_status": "string",
          "work_auth": "string",
          "languages": [{{ "name": "string", "level": number }}],
          "it_skills": ["string"],
          "certifications": ["string"],
          "strengths": ["string"]
        }}
        """
        
        try:
            cv_context = await self.llm.generate_json(parse_prompt)
            if "error" in cv_context:
                raise ValueError("Could not parse edited CV")
            
            # Re-add image data URI which isn't in markdown
            cv_context["name"] = user.full_name
            cv_context["profile_picture_url"] = self._get_image_data_uri(profile.profile_picture_url) if profile else None
            
            # Generate new PDFs
            upload_dir = os.path.join("uploads", str(user_id), "applications", str(application_id))
            os.makedirs(upload_dir, exist_ok=True)
            
            cv_filename = f"Tailored_CV_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            cl_filename = f"Cover_Letter_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            cv_path = os.path.join(upload_dir, cv_filename)
            cl_path = os.path.join(upload_dir, cl_filename)
            
            cl_context = {
                "name": user.full_name,
                "location": cv_context.get('location', ''),
                "phone": cv_context.get('phone', ''),
                "email": user.email,
                "company": company,
                "job_title": job_title,
                "content": cl_text,
                "date": datetime.now().strftime("%B %d, %Y")
            }

            cv_success = await self.pdf_service.create_cv_pdf(cv_context, cv_path)
            cl_success = await self.pdf_service.create_cl_pdf(cl_context, cl_path)
            
            if cv_success:
                app.cv_path = cv_path
            if cl_success:
                app.cl_path = cl_path
                
            app.tailored_cv = cv_text
            app.cover_letter = cl_text
            app.generated_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "status": "success",
                "cv_path": app.cv_path,
                "cl_path": app.cl_path
            }
        except Exception as e:
            logger.error(f"Re-generation failed: {e}")
            return {"status": "error", "message": str(e)}
