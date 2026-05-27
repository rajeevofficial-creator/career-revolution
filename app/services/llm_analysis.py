"""
LLM Analysis Service — document and career data extraction.

Wraps the LLMBridge so callers don't need to know which provider is active.
Existing API (analyze_text, analyze_file, generate_json, etc.) is preserved
for backward compatibility with JobPreparationAgent and other callers.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy import of the bridge — avoids import-time failures if SDKs missing
_bridge = None

def _get_bridge():
    global _bridge
    if _bridge is None:
        from agents.core.llm_bridge import build_bridge_from_settings
        _bridge = build_bridge_from_settings()
    return _bridge

class LLMAnalysisService:
    """
    Service for career document analysis and UI decision making.
    Delegates to LLMBridge for provider-agnostic calls.
    Keeps the legacy Gemini model reference for methods that need it directly
    (analyze_file uses the SDK's multimodal API directly).
    """

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = None

        # Keep a direct Gemini model for multimodal file analysis (PDF/image bytes)
        # which uses the SDK's native format rather than base64 encoding.
        if self.api_key and getattr(settings, "llm_provider", "gemini") == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                for model_name in ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"]:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        break
                    except Exception:
                        continue
            except ImportError:
                pass

        if not self.model:
            logger.warning("LLMAnalysisService: no direct Gemini model — file analysis will use bridge.")

        self.json_schema = """
        {
            "personal_info": {
                "name": "string or null",
                "email": "string or null",
                "phone": "string or null",
                "location": "string or null",
                "summary": "a professional summary of the candidate (max 3 sentences)",
                "linkedin_url": "string or null",
                "sector": "the broad sector the user works in (e.g., Technology, Healthcare, Finance) or null",
                "industry": "the specific industry the user works in (e.g., Software, Pharmaceuticals, Banking) or null"
            },
            "skills": ["list of technical and soft skills"],
            "experience": [
                {
                    "title": "specific project role or job title",
                    "company": "client name or employer name",
                    "start_date": "YYYY or YYYY-MM or null",
                    "end_date": "YYYY or YYYY-MM or 'Present' or null",
                    "description": "short description of responsibilities and achievements"
                }
            ],
            "education": [
                {
                    "institution": "university/school name",
                    "degree": "degree name",
                    "start_date": "YYYY or null",
                    "end_date": "YYYY or null"
                }
            ],
            "certifications": [
                {
                    "name": "certification name",
                    "issuer": "issuing organization",
                    "date": "YYYY-MM or null"
                }
            ]
        }
        """

    def is_available(self) -> bool:
        """Check if the LLM service is configured and available."""
        return self.model is not None or _get_bridge().is_available()

    async def analyze_text(self, text: str, document_context: str = "CV/Resume") -> Dict[str, Any]:
        """Analyze document text using Gemini and extract structured data."""
        if not self.is_available():
            return {"error": "LLM service not configured"}

        prompt = f"""
        Analyze the following text from a {document_context} and extract career-related information.
        IMPORTANT:
        - Look carefully for contact information (Email, Phone, Location, LinkedIn) which may be at the very top or bottom of the text.
        - For Experiences: Distinguish between the 'Company' (the employer or client) and the 'Title' (your specific role).
        - For Education: Extract institution, degree, and specific graduation years or months.
        - For Dates: Look for year ranges like '2023-2024'. If a date is missing, return null. Do NOT make up dates.
        
        Return the result ONLY as a valid JSON object with this exact structure:
        {self.json_schema}

        Document Text:
        ---
        {text}
        ---
        """
        return await self._get_gemini_response(prompt)

    async def generate_json(self, prompt: str) -> Dict[str, Any]:
        """
        Generic method to get a JSON response from Gemini without resume-specific wrapping.
        Expects the prompt to define the JSON structure.
        """
        if not self.is_available():
            return {"error": "LLM service not configured"}
        return await self._get_gemini_response(prompt)

    async def verify_alignment(self, content: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deeply verify if a job description fits a user profile."""
        if not self.is_available():
            return {"is_perfect_match": False, "reason": "LLM skip"}

        prompt = f"""
        Analyze this Job Description against the User Profile.
        
        User Profile:
        {json.dumps(profile_data, indent=2)}
        
        Job Description:
        ---
        {content[:4000]} # Limit for context window
        ---
        
        Task:
        1. Is this a strong match (85%+) for the user's skills and desired role?
        2. Extracted Job Title: (The actual title from the text)
        3. Extracted Company: (The actual company from the text)
        4. Summary of why matching:
        
        Return JSON object:
        {{
            "is_perfect_match": boolean,
            "match_score": 0-100,
            "extracted_title": "string",
            "extracted_company": "string",
            "reason": "string",
            "critical_skills_found": ["list"]
        }}
        """
        return await self._get_gemini_response(prompt)

    async def analyze_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """Analyze a document image (e.g., certificate or CV page) using Gemini Vision."""
        return await self.analyze_file(image_bytes, mime_type)

    async def analyze_file(self, file_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        """Analyze a document file (image or PDF) using Gemini Vision/Multimodal."""
        if not self.is_available():
            return {"error": "LLM service not configured"}

        prompt = f"""
        Analyze this document and extract career information. 
        IMPORTANT: 
        - If this is a CV or Resume, look for contact details (Phone, Email, LinkedIn, Address) which are often located in a sidebar, column, or header.
        - For Experiences: Differentiate between the Client/Company and your specific Role in each project.
        - For Education: Extract institution, degree, and specific graduation years or months.
        - For Dates: Extract year or month intervals accurately.
        
        Return the result ONLY as a valid JSON object with this exact structure:
        {self.json_schema}
        """

        try:
            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": mime_type,
                    "data": file_bytes
                }
            ])
            return self._parse_json_response(response.text)
        except Exception as e:
            # Catch 404 and try gemini-pro (may not support vision in same way, but it's a start)
            if "404" in str(e) and "gemini-3-flash-preview" in str(self.model.model_name):
                logger.warning("Gemini 3 Flash Preview 404. Falling back to Gemini 3.5 Flash.")
                self.model = genai.GenerativeModel('gemini-3.5-flash')
                return self.analyze_vision(prompt, file_bytes, mime_type)
            logger.error(f"Error during LLM vision analysis: {e}")
            return {"error": str(e)}

    async def validate_job_page_image(self, screenshot_bytes: bytes, country: str = "Switzerland") -> Dict[str, Any]:
        """
        Use Gemini Vision to visually validate that a page screenshot shows actual job listings
        filtered to a specific country.

        Returns:
            {
                "shows_job_listings": bool,
                "country_specific": bool,
                "job_count_estimate": int or null,
                "confidence": "high|medium|low",
                "notes": "short explanation"
            }
        """
        if not self.is_available():
            return {"error": "LLM service not configured"}

        prompt = f"""
You are a QA engineer validating a job search portal page for the Career Revolution platform.

Look at this screenshot of a web page and answer the following questions:

1. Does this page show a LIST of job openings/vacancies (not just a careers landing page or homepage)?
2. Do the jobs appear to be filtered or targeted to {country} specifically?
   (Look for country filters, location labels, city names in {country}, or URL/breadcrumb indicators.)
3. Approximately how many job listings are visible on the page?

Return ONLY a valid JSON object:
{{
    "shows_job_listings": true or false,
    "country_specific": true or false,
    "job_count_estimate": number or null,
    "confidence": "high" or "medium" or "low",
    "notes": "1-2 sentence explanation of what the page shows"
}}
"""
        try:
            response = self.model.generate_content([
                prompt,
                {"mime_type": "image/png", "data": screenshot_bytes}
            ])
            # Check for non-standard finish reasons (safety filters, etc.)
            candidate = response.candidates[0] if response.candidates else None
            if candidate and hasattr(candidate, "finish_reason") and candidate.finish_reason not in (0, 1):
                notes = f"Gemini non-standard finish_reason={candidate.finish_reason}"
                logger.warning(f"validate_job_page_image: {notes} for response")
                return {"shows_job_listings": None, "country_specific": False, "confidence": "low",
                        "notes": notes, "job_count_estimate": None, "api_error": notes}

            result = self._parse_json_response(response.text)
            if isinstance(result, dict) and "shows_job_listings" in result:
                return result
            # Parse failed — inconclusive, not a hard failure
            return {"shows_job_listings": None, "country_specific": False, "confidence": "low",
                    "notes": "Could not parse LLM response", "job_count_estimate": None}
        except Exception as e:
            logger.error(f"Visual job page validation failed: {e}")
            return {"error": str(e), "shows_job_listings": None}

    async def identify_ui_element(self, screenshot_bytes: bytes, goal_description: str) -> Dict[str, Any]:
        """
        Use vision to identify an interactive UI element from a labeled screenshot.
        Routes through LLMBridge (provider-agnostic).
        """
        if not self.is_available():
            return {"error": "LLM service not configured"}

        from agents.core.llm_bridge import LLMTier
        prompt = f"""
You are an AI browser assistant. I need to perform a specific action on this web page.
GOAL: {goal_description}

TASK:
1. Look at the screenshot. Many interactive elements have small colored labels with numbers (e.g. [1], [2], [15]).
2. Identify the EXACT element that corresponds to the GOAL.
   - For "Click the apply button": look for "Apply", "Easy Apply", "Jetzt bewerben", "Postuler", "I'm interested".
3. Return the number inside the label for that element (e.g. if the label is [15], return "15").

Return ONLY valid JSON:
{{
    "element_id": "number_as_string or null",
    "element_type": "button|link|input|unknown",
    "confidence": 0-100,
    "reasoning": "short explanation"
}}
"""
        return await _get_bridge().vision(prompt, screenshot_bytes, LLMTier.VISION)

    async def decide_universal_apply_action(
        self,
        screenshot_bytes: bytes,
        page_url: str,
        user_profile: Dict[str, Any],
        step_history: List[str],
    ) -> Dict[str, Any]:
        """
        Legacy entry point kept for backward compatibility.
        New code should use ApplyOrchestrator directly.
        Routes through LLMBridge (provider-agnostic).
        """
        if not self.is_available():
            return {"error": "LLM service not configured"}

        from agents.core.llm_bridge import LLMTier
        safe_profile = {k: v for k, v in user_profile.items()
                        if k not in ("linkedin_password", "email_password")}
        prompt = f"""
You are an autonomous Job Application Agent completing a job application.

USER PROFILE:
{json.dumps(safe_profile, indent=2)}

CONTEXT:
- URL: {page_url}
- Recent steps: {", ".join(step_history[-5:]) if step_history else "Start"}

Interactive elements are labeled [N]. Identify the next single action.

AVAILABLE ACTIONS: TYPE | CLICK | UPLOAD | SELECT | WAIT | FINISH_SUCCESS | INTERVENTION

Return ONLY valid JSON:
{{
    "action": "TYPE|CLICK|UPLOAD|SELECT|WAIT|FINISH_SUCCESS|INTERVENTION",
    "element_id": "string or null",
    "value": "string or null",
    "reasoning": "one sentence",
    "is_success_page": false,
    "current_stage": "LOGIN|REGISTER|PERSONAL_INFO|EXPERIENCE|QUESTIONS|REVIEW|SUCCESS",
    "account_metadata": {{
        "is_creating_account": false,
        "platform_name": null,
        "username": null,
        "password": null
    }}
}}
"""
        result = await _get_bridge().vision(prompt, screenshot_bytes, LLMTier.VISION)
        if "error" in result:
            return {"action": "INTERVENTION", "reason": result["error"]}
        return result

    async def _get_gemini_response(self, prompt: str) -> Dict[str, Any]:
        """Route a text prompt through the LLMBridge (provider-agnostic)."""
        from agents.core.llm_bridge import LLMTier
        result = await _get_bridge().text(prompt, LLMTier.MICRO)
        if "error" in result and self.model:
            # Bridge failed but we have a direct Gemini model — try directly
            try:
                response = self.model.generate_content(prompt)
                return self._parse_json_response(response.text)
            except Exception as e:
                logger.error(f"Direct Gemini fallback failed: {e}")
        return result

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from Gemini response text."""
        try:
            # Look for JSON code blocks first
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.rfind('```')
                json_data = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.rfind('```')
                json_data = response_text[json_start:json_end].strip()
            else:
                # Fallback to finding braces or brackets
                bracket_start = response_text.find('[')
                brace_start = response_text.find('{')
                
                # Pick the first one that appears
                if bracket_start != -1 and brace_start != -1:
                    json_start = min(bracket_start, brace_start)
                else:
                    json_start = bracket_start if bracket_start != -1 else brace_start
                
                # Find the matching end
                if json_start == bracket_start:
                    json_end = response_text.rfind(']') + 1
                else:
                    json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_data = response_text[json_start:json_end]
                else:
                    logger.error(f"Could not find JSON in Gemini response: {response_text}")
                    return {"error": "Invalid response format from LLM"}
            
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Error parsing Gemini JSON: {e}")
            return {"error": f"JSON Parse Error: {str(e)}"}
