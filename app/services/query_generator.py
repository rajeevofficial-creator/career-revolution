"""
Service for generating optimized Boolean search queries based on user profiles.
Implements Stage A of the Super-Agent v2.0 Job Discovery Pipeline.
"""

import logging
from typing import List, Dict, Any
from app.services.llm_analysis import LLMAnalysisService
from app.models.database import UserProfile

logger = logging.getLogger(__name__)

class QueryGeneratorService:
    """Service for expanding job titles into a Search Matrix of Boolean queries."""
    
    def __init__(self):
        self.llm = LLMAnalysisService()

    async def generate_search_matrix(self, profile: UserProfile, source_domain: str = None) -> List[str]:
        """
        Generates 5-10 optimized Boolean search strings for a specific profile and source.
        """
        from datetime import datetime, timedelta
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # REFINED: Ensure we search at the country level
        target_loc = profile.location or "Switzerland"
        
        # Build the prompt for Stage A
        prompt = f"""
        Role: Expert Boolean Search Engineer & Recruitment Strategist.
        
        Task: Generate 5-10 distinct, high-precision Google Dorking queries for job discovery.
        Targeting: {profile.desired_job_title}
        Location Context: {target_loc} (Include major cities in this region as sub-filters)
        Candidate Summary: {profile.summary[:500]}
        
        Rules:
        1. Use site: operators if domain is provided (Target Domain: {source_domain or 'Any'}).
        2. Use intitle: for core keywords.
        3. Use Boolean operators (OR, AND).
        4. Focus on the COUNTRY level for {target_loc} to ensure maximum reach.
        5. Include local variations (e.g., if Switzerland, use Schweiz/CH; if Germany, use Deutschland/DE).
        
        Output: A JSON array of strings ONLY.
        """
        
        try:
            logger.info(f"Generating search matrix for {profile.desired_job_title} in {target_loc}...")
            response = await self.llm._get_gemini_response(prompt)
            
            if isinstance(response, list):
                queries = [str(q) for q in response if q]
                return queries
            
            return [f'"{profile.desired_job_title}" {target_loc}']
            
        except Exception as e:
            logger.error(f"Failed to generate search matrix: {e}")
            return [f'"{profile.desired_job_title}" {target_loc}']
