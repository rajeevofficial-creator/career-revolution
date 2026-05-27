"""
Triage Service for Stage C of the Super-Agent v2.0 Pipeline.
Uses Gemini to filter search results based on snippets before deep scraping.
"""

import logging
import json
from typing import List, Dict, Any
from app.services.llm_analysis import LLMAnalysisService
from app.models.database import UserProfile

logger = logging.getLogger(__name__)

class TriageService:
    """Service for filtering discovery results based on search snippets."""
    
    def __init__(self):
        self.llm = LLMAnalysisService()

    async def triage_results(self, results: List[Dict[str, Any]], profile: UserProfile) -> List[Dict[str, Any]]:
        """
        Takes a list of search results and returns ALL matches that meet the relevance threshold.
        Uses a batching strategy to handle large volumes (300+ candidates).
        """
        if not results:
            return []
            
        triaged_indices = []
        batch_size = 20 # Optimal for context and speed
        
        for i in range(0, len(results), batch_size):
            batch = results[i:i+batch_size]
            logger.info(f"Triaging batch {i//batch_size + 1}: {len(batch)} candidates...")
            
            snippets_text = ""
            for j, res in enumerate(batch):
                snippets_text += f"{j}. [{res['title']}] - {res['snippet']} (URL: {res['url']})\n\n"
            
            prompt = f"""
            Role: Senior Talent Scout & Triage Analyst.
            
            Task: Analyze the following search results and identify ALL job postings that are a strong match for this candidate.
            
            Candidate Profile:
            - Target Role: {profile.desired_job_title}
            - Seniority Level: {profile.experience_level or 'Professional'}
            - Location: {profile.location}
            
            Search Results (Batch):
            {snippets_text}
            
            Instructions:
            1. Identify ALL indices (0-{len(batch)-1}) that represent a clear professional match.
            2. Criteria: Correct Seniority, Correct Sector, and Correct Location (if specified).
            3. STRICT FORMAT FILTER: Exclude landing pages, search results, or "50+ Jobs" aggregates.
            4. Return ONLY a JSON array of indices.
            
            Example: [0, 2, 5, 12, 19]
            """
            
            try:
                batch_indices = await self.llm._get_gemini_response(prompt)
                if isinstance(batch_indices, list):
                    for idx in batch_indices:
                        try:
                            # Map batch index back to original list index
                            orig_idx = i + int(idx)
                            if i <= orig_idx < i + len(batch):
                                triaged_indices.append(orig_idx)
                        except (ValueError, TypeError): continue
            except Exception as e:
                logger.error(f"Batch triage failed at {i}: {e}")
                # Fallback: include all in this batch if it's very small
                if len(batch) < 5: triaged_indices.extend(range(i, i+len(batch)))

        # Final selection
        unique_indices = list(dict.fromkeys(triaged_indices))
        final_triaged = [results[idx] for idx in unique_indices]
        
        logger.info(f"Triage complete. Selected {len(final_triaged)} candidates from {len(results)}.")
        return final_triaged
