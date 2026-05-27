"""
SocialContentAgent — AI-powered social visibility content creation.

Capabilities:
  - Suggest topic ideas tailored to the user's experience and target roles
  - Generate LinkedIn articles, short posts, and threads
  - Score and audit generated content before saving
  - Format output per platform (LinkedIn, Medium, Twitter/X, GitHub)
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.database import (
    User, UserProfile, UserExperience, UserSkill,
    SocialTopicIdea, SocialContentPiece,
)
from app.services.llm_analysis import LLMAnalysisService

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Tone presets
# ─────────────────────────────────────────────────────────────────────────────
TONE_DESCRIPTIONS = {
    "thought_leader": "authoritative, insightful, data-backed — the voice of a senior practitioner sharing hard-won knowledge",
    "conversational": "warm, accessible, first-person — like a candid post from a trusted colleague",
    "professional": "formal, precise, structured — appropriate for corporate or B2B audiences",
    "storytelling": "narrative-driven, personal, uses a problem→journey→resolution arc",
}

PLATFORM_CONSTRAINTS = {
    "linkedin": {
        "article": {"min_words": 700, "max_words": 1400, "format": "markdown with ## subheadings"},
        "post":    {"min_words": 80,  "max_words": 280,  "format": "plain text with line breaks, no headers"},
    },
    "twitter": {
        "post":    {"min_words": 20,  "max_words": 60,   "format": "concise, punchy, single insight"},
        "thread":  {"min_words": 150, "max_words": 350,  "format": "numbered tweets 1/ 2/ 3/ ... format"},
    },
    "medium": {
        "article": {"min_words": 900, "max_words": 2000, "format": "markdown with # title, ## sections, SEO-friendly"},
    },
    "github": {
        "about":   {"min_words": 30,  "max_words": 80,   "format": "plain text, 3 lines max"},
    },
}


class SocialContentAgent:

    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMAnalysisService()

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_user_context(self, user_id: int) -> dict:
        """Compile a compact profile snapshot for LLM prompts."""
        user = self.db.query(User).filter(User.id == user_id).first()
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        experiences = self.db.query(UserExperience).filter(UserExperience.user_id == user_id).all()
        skills = self.db.query(UserSkill).filter(UserSkill.user_id == user_id).all()

        exp_lines = []
        for e in experiences[:6]:
            line = f"- {e.position} at {e.company}"
            if e.start_date:
                end = e.end_date.strftime("%Y") if e.end_date else "Present"
                line += f" ({e.start_date.strftime('%Y')}–{end})"
            exp_lines.append(line)

        return {
            "name": user.full_name if user else "Professional",
            "current_role": profile.current_job_title if profile else "",
            "target_role": profile.desired_job_title if profile else "",
            "summary": (profile.summary or "")[:400] if profile else "",
            "location": profile.location if profile else "",
            "industry": profile.industry if profile else "",
            "experience_years": len(experiences),
            "recent_experience": "\n".join(exp_lines),
            "technical_skills": [s.skill_name for s in skills if s.category == "technical"][:15],
            "soft_skills": [s.skill_name for s in skills if s.category == "soft"][:8],
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Topic suggestion
    # ─────────────────────────────────────────────────────────────────────────

    async def suggest_topics(self, user_id: int, count: int = 10) -> list[dict]:
        """
        Generate AI-suggested topic ideas grounded in the user's actual experience.
        Saves them to DB and returns the list.
        """
        ctx = self._build_user_context(user_id)

        prompt = f"""
You are a LinkedIn content strategist helping a professional build their thought leadership presence.

USER PROFILE:
- Name: {ctx['name']}
- Current role: {ctx['current_role']}
- Target role: {ctx['target_role']}
- Industry: {ctx['industry']}
- Years of experience: {ctx['experience_years']}
- Summary: {ctx['summary']}
- Recent experience:
{ctx['recent_experience']}
- Technical skills: {', '.join(ctx['technical_skills'])}

TASK: Generate exactly {count} topic ideas this person should write about on LinkedIn.
Each idea must:
1. Be grounded in their ACTUAL experience (no generic platitudes)
2. Demonstrate authority in their domain
3. Be interesting enough that peers would stop scrolling

For each topic return:
- title: compelling article/post title (max 12 words)
- summary: 2-sentence hook explaining why THIS person can write this and why readers care
- category: one of [thought_leadership, how_to, case_study, career_story, industry_insight]
- relevance_score: 1-10 (how well it fits their profile and target role)
- suggested_platform: linkedin_article | linkedin_post | medium
- suggested_tone: thought_leader | conversational | professional | storytelling

Return ONLY a valid JSON object: {{ "topics": [ ... ] }}
"""
        result = await self.llm.generate_json(prompt)
        topics_raw = result.get("topics", [])

        saved = []
        for t in topics_raw[:count]:
            idea = SocialTopicIdea(
                user_id=user_id,
                title=t.get("title", "Untitled"),
                summary=t.get("summary", ""),
                source="ai_suggested",
                category=t.get("category", "thought_leadership"),
                relevance_score=int(t.get("relevance_score", 7)),
            )
            self.db.add(idea)
            self.db.flush()
            saved.append({
                "id": idea.id,
                "title": idea.title,
                "summary": idea.summary,
                "category": idea.category,
                "relevance_score": idea.relevance_score,
                "source": "ai_suggested",
                "suggested_platform": t.get("suggested_platform", "linkedin"),
                "suggested_tone": t.get("suggested_tone", "thought_leader"),
            })

        self.db.commit()
        return saved

    async def save_user_topic(self, user_id: int, title: str, summary: str = "") -> dict:
        """Save a manually-entered topic from the user."""
        idea = SocialTopicIdea(
            user_id=user_id,
            title=title,
            summary=summary,
            source="user_provided",
            category="thought_leadership",
            relevance_score=8,
        )
        self.db.add(idea)
        self.db.commit()
        self.db.refresh(idea)
        return {
            "id": idea.id,
            "title": idea.title,
            "summary": idea.summary,
            "category": idea.category,
            "relevance_score": idea.relevance_score,
            "source": "user_provided",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Content generation
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_content(
        self,
        user_id: int,
        topic_id: Optional[int] = None,
        custom_topic: Optional[str] = None,
        content_type: str = "article",   # article | post | thread
        platform: str = "linkedin",      # linkedin | twitter | medium | github
        tone: str = "thought_leader",
    ) -> dict:
        """
        Generate a full content piece using the LLM.
        Returns the saved SocialContentPiece as a dict.
        """
        ctx = self._build_user_context(user_id)
        tone_desc = TONE_DESCRIPTIONS.get(tone, TONE_DESCRIPTIONS["thought_leader"])
        constraints = PLATFORM_CONSTRAINTS.get(platform, {}).get(content_type, {
            "min_words": 200, "max_words": 600, "format": "markdown"
        })

        # Resolve topic
        topic_title, topic_summary, topic_idea_id = "", "", None
        if topic_id:
            idea = self.db.query(SocialTopicIdea).filter(
                SocialTopicIdea.id == topic_id,
                SocialTopicIdea.user_id == user_id
            ).first()
            if idea:
                topic_title = idea.title
                topic_summary = idea.summary or ""
                topic_idea_id = idea.id
                idea.used = True
                self.db.commit()
        if custom_topic:
            topic_title = custom_topic

        if not topic_title:
            return {"error": "No topic provided"}

        # Platform-specific structure instructions
        structure_instructions = _get_structure_instructions(content_type, platform, constraints)

        prompt = f"""
You are a world-class ghostwriter producing content for a senior professional.

AUTHOR PROFILE:
- Name: {ctx['name']}
- Role: {ctx['current_role']} → targeting {ctx['target_role']}
- Industry: {ctx['industry']}
- Experience: {ctx['experience_years']} years
- Recent roles:
{ctx['recent_experience']}
- Key skills: {', '.join(ctx['technical_skills'][:10])}

TOPIC: {topic_title}
TOPIC CONTEXT: {topic_summary}

PLATFORM: {platform.upper()}
CONTENT TYPE: {content_type.upper()}
TONE: {tone_desc}
TARGET LENGTH: {constraints['min_words']}–{constraints['max_words']} words
FORMAT: {constraints['format']}

{structure_instructions}

CRITICAL RULES:
- Write AS this person — first-person, grounded in their real background
- Every insight must feel earned from their experience, NOT generic advice
- No clichés: avoid "passionate", "excited to share", "in today's fast-paced world"
- End with a question or CTA that invites comments/engagement
- The content must make a peer with 20 years in this field nod and think "that's true"

Return ONLY a valid JSON object with these keys:
{{
  "title": "Final title for the piece",
  "body": "The full content ({constraints['format']})",
  "hook_a": "Opening hook variant A (first 1-2 sentences, punchy)",
  "hook_b": "Opening hook variant B (different angle)",
  "hashtags": ["tag1", "tag2", ...],  // 8-12 relevant hashtags WITHOUT # symbol
  "word_count": <integer>,
  "estimated_read_minutes": <integer>,
  "ai_score": <1-10 quality score>,
  "ai_feedback": "One sentence on what makes this piece strong"
}}
"""

        result = await self.llm.generate_json(prompt)

        if "error" in result:
            return {"error": result["error"]}

        # Persist
        piece = SocialContentPiece(
            user_id=user_id,
            topic_idea_id=topic_idea_id,
            title=result.get("title", topic_title),
            content_type=content_type,
            platform=platform,
            status="draft",
            body=result.get("body", ""),
            hook_a=result.get("hook_a", ""),
            hook_b=result.get("hook_b", ""),
            hashtags=json.dumps(result.get("hashtags", [])),
            word_count=result.get("word_count"),
            estimated_read_minutes=result.get("estimated_read_minutes"),
            ai_score=result.get("ai_score"),
            ai_feedback=result.get("ai_feedback", ""),
            tone=tone,
            generation_context=json.dumps({
                "topic": topic_title,
                "platform": platform,
                "content_type": content_type,
                "tone": tone,
            }),
        )
        self.db.add(piece)
        self.db.commit()
        self.db.refresh(piece)

        return _piece_to_dict(piece)

    # ─────────────────────────────────────────────────────────────────────────
    # Content management
    # ─────────────────────────────────────────────────────────────────────────

    def list_content(self, user_id: int, status: Optional[str] = None,
                     platform: Optional[str] = None, content_type: Optional[str] = None) -> list[dict]:
        q = self.db.query(SocialContentPiece).filter(SocialContentPiece.user_id == user_id)
        if status:
            q = q.filter(SocialContentPiece.status == status)
        if platform:
            q = q.filter(SocialContentPiece.platform == platform)
        if content_type:
            q = q.filter(SocialContentPiece.content_type == content_type)
        return [_piece_to_dict(p) for p in q.order_by(SocialContentPiece.created_at.desc()).all()]

    def get_content(self, user_id: int, piece_id: int) -> Optional[dict]:
        p = self.db.query(SocialContentPiece).filter(
            SocialContentPiece.id == piece_id,
            SocialContentPiece.user_id == user_id
        ).first()
        return _piece_to_dict(p) if p else None

    def update_content(self, user_id: int, piece_id: int, updates: dict) -> Optional[dict]:
        p = self.db.query(SocialContentPiece).filter(
            SocialContentPiece.id == piece_id,
            SocialContentPiece.user_id == user_id
        ).first()
        if not p:
            return None
        allowed = ["title", "body", "hook_a", "hook_b", "hashtags", "status",
                   "scheduled_at", "published_at", "published_url", "engagement_notes"]
        for key, val in updates.items():
            if key in allowed:
                if key == "hashtags" and isinstance(val, list):
                    val = json.dumps(val)
                setattr(p, key, val)
        p.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(p)
        return _piece_to_dict(p)

    def delete_content(self, user_id: int, piece_id: int) -> bool:
        p = self.db.query(SocialContentPiece).filter(
            SocialContentPiece.id == piece_id,
            SocialContentPiece.user_id == user_id
        ).first()
        if not p:
            return False
        self.db.delete(p)
        self.db.commit()
        return True

    def get_dashboard(self, user_id: int) -> dict:
        """Aggregate stats for the Visibility Score panel."""
        all_pieces = self.db.query(SocialContentPiece).filter(
            SocialContentPiece.user_id == user_id
        ).all()
        published = [p for p in all_pieces if p.status == "published"]
        scheduled = [p for p in all_pieces if p.status == "scheduled"]
        drafts = [p for p in all_pieces if p.status == "draft"]
        topics = self.db.query(SocialTopicIdea).filter(
            SocialTopicIdea.user_id == user_id
        ).count()

        # Display avg across all pieces
        all_scores = [p.ai_score for p in all_pieces if p.ai_score]
        avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0

        # Visibility score: ONLY published content counts
        # Drafts and scheduled do NOT move the score — actual published presence does
        pub_scores = [p.ai_score for p in published if p.ai_score]
        avg_pub_score = round(sum(pub_scores) / len(pub_scores), 1) if pub_scores else 0
        published_platforms = set(p.platform for p in published)

        pub_count_score = min(len(published) * 12, 60)              # up to 60 pts — quantity published
        platform_diversity = min(len(published_platforms) * 8, 24)  # up to 24 pts — cross-platform reach
        quality_score = int((avg_pub_score / 10) * 16)              # up to 16 pts — quality of published
        visibility = pub_count_score + platform_diversity + quality_score

        next_scheduled = None
        future = [p for p in scheduled if p.scheduled_at and p.scheduled_at > datetime.utcnow()]
        if future:
            next_scheduled = min(future, key=lambda p: p.scheduled_at).scheduled_at.isoformat()

        by_platform: dict = {}
        for p in all_pieces:
            by_platform.setdefault(p.platform, 0)
            by_platform[p.platform] += 1

        by_type: dict = {}
        for p in all_pieces:
            by_type.setdefault(p.content_type, 0)
            by_type[p.content_type] += 1

        return {
            "visibility_score": min(visibility, 100),
            "total_pieces": len(all_pieces),
            "published": len(published),
            "scheduled": len(scheduled),
            "drafts": len(drafts),
            "topics_available": topics,
            "avg_ai_quality_score": avg_score,
            "next_scheduled": next_scheduled,
            "by_platform": by_platform,
            "by_type": by_type,
        }

    def list_topics(self, user_id: int) -> list[dict]:
        ideas = self.db.query(SocialTopicIdea).filter(
            SocialTopicIdea.user_id == user_id
        ).order_by(SocialTopicIdea.relevance_score.desc()).all()
        return [_topic_to_dict(t) for t in ideas]

    def delete_topic(self, user_id: int, topic_id: int) -> bool:
        t = self.db.query(SocialTopicIdea).filter(
            SocialTopicIdea.id == topic_id,
            SocialTopicIdea.user_id == user_id
        ).first()
        if not t:
            return False
        self.db.delete(t)
        self.db.commit()
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_structure_instructions(content_type: str, platform: str, constraints: dict) -> str:
    if platform == "linkedin" and content_type == "article":
        return """
ARTICLE STRUCTURE (LinkedIn):
1. Hook paragraph (2-3 sentences) — start with a counterintuitive statement or bold claim
2. The Problem / Context (1 paragraph)
3. 2-4 sections with ## subheadings — each section makes ONE clear point with a real example
4. Key Takeaways (3-5 bullet points)
5. Closing CTA — end with an engaging question to the reader
"""
    if platform == "linkedin" and content_type == "post":
        return """
POST STRUCTURE (LinkedIn):
Line 1: Hook — one powerful sentence (no "I am excited to share")
[blank line]
Lines 2-6: 3-4 insight lines OR a short story (one insight per line, use line breaks not bullets)
[blank line]
Final line: Engaging question OR clear CTA
"""
    if platform == "twitter" and content_type == "thread":
        return """
THREAD STRUCTURE (Twitter/X):
1/ Hook tweet — bold claim or surprising insight
2/-N/: Each tweet = one idea, punchy, self-contained
Final tweet: Summary + question or CTA
"""
    if platform == "medium" and content_type == "article":
        return """
ARTICLE STRUCTURE (Medium/Blog):
# Title (SEO-optimised, 8-12 words)
Intro paragraph — what the reader will learn and why it matters
## Section 1 (practical)
## Section 2 (deeper insight)
## Section 3 (application / example)
## Key Takeaways
Closing paragraph with CTA
"""
    return "Write in a clear, structured format appropriate for the platform."


def _piece_to_dict(p: SocialContentPiece) -> dict:
    hashtags = []
    try:
        hashtags = json.loads(p.hashtags) if p.hashtags else []
    except Exception:
        pass
    return {
        "id": p.id,
        "user_id": p.user_id,
        "topic_idea_id": p.topic_idea_id,
        "title": p.title,
        "content_type": p.content_type,
        "platform": p.platform,
        "status": p.status,
        "body": p.body,
        "hook_a": p.hook_a,
        "hook_b": p.hook_b,
        "hashtags": hashtags,
        "word_count": p.word_count,
        "estimated_read_minutes": p.estimated_read_minutes,
        "ai_score": p.ai_score,
        "ai_feedback": p.ai_feedback,
        "tone": p.tone,
        "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "published_url": p.published_url,
        "engagement_notes": p.engagement_notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _topic_to_dict(t: SocialTopicIdea) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "summary": t.summary,
        "category": t.category,
        "relevance_score": t.relevance_score,
        "source": t.source,
        "used": t.used,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
