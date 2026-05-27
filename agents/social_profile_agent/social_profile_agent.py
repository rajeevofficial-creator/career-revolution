"""
Social Profile Agent for Career Revolution
Professional brand building and content creation agent.
"""

import os
import json
import re
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict, field


class ContentType(Enum):
    """Types of content that can be created."""
    LINKEDIN_ARTICLE = "linkedin_article"
    LINKEDIN_POST = "linkedin_post"
    YOUTUBE_SCRIPT = "youtube_script"
    BLOG_POST = "blog_post"
    GENERIC = "generic"


class ContentStatus(Enum):
    """Status of content pieces."""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


@dataclass
class ContentPiece:
    """Data class representing a piece of content."""
    id: str
    title: str
    content_type: ContentType
    content: str
    status: ContentStatus
    created_at: datetime
    tags: List[str] = field(default_factory=list)
    target_platforms: List[str] = field(default_factory=list)
    scheduled_for: Optional[datetime] = None
    published_at: Optional[datetime] = None


class SocialProfileAgent:
    """Agent for professional brand building and content creation."""
    
    def __init__(self, profile_data_path: str = "shared_data/profile/master_profile.json",
                 output_path: str = "shared_data/content"):
        """Initialize the social profile agent."""
        self.profile_data_path = profile_data_path
        self.output_path = output_path
        
        # Load profile data
        self.profile = self._load_profile_data()
        
        # Content ideas database
        self.content_ideas = []
        self.content_pieces = []
        self.content_calendar = []
        
        # Topic categories based on profile
        self.topic_categories = self._generate_topic_categories()
        
        # Target platforms
        self.target_platforms = ["LinkedIn", "YouTube", "Professional Blog"]
        
        # Create output directories
        self._create_output_directories()
    
    def _load_profile_data(self) -> Dict[str, Any]:
        """Load profile data from file."""
        try:
            with open(self.profile_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Profile data not found at {self.profile_data_path}")
            return {
                'skills': {'detailed': {'technical': [], 'management': [], 'industry_specific': []}},
                'experience': {'max_years': 10},
                'education': {'highest_level': 'master'},
                'industries': {'primary': 'pharma_it'}
            }
    
    def _create_output_directories(self):
        """Create necessary output directories."""
        directories = [
            os.path.join(self.output_path, "drafts"),
            os.path.join(self.output_path, "approved"),
            os.path.join(self.output_path, "scheduled"),
            os.path.join(self.output_path, "published"),
            os.path.join(self.output_path, "analytics")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _generate_topic_categories(self) -> List[str]:
        """Generate topic categories based on profile."""
        categories = []
        
        # Add industry-specific topics
        primary_industry = self.profile.get('industries', {}).get('primary', '')
        if primary_industry:
            industry_map = {
                'pharma_it': 'Pharmaceutical IT & Digital Health',
                'finance_it': 'Financial Technology & IT Strategy',
                'digital_transformation': 'Digital Innovation & Business Transformation',
                'consulting': 'Management Consulting & Strategic Advisory',
                'it_services': 'IT Service Delivery & Client Management'
            }
            categories.append(industry_map.get(primary_industry, 'Industry Leadership'))
        
        # Add skill-based topics
        skills_data = self.profile.get('skills', {}).get('detailed', {})
        
        if skills_data.get('management'):
            categories.append('Leadership & Team Management')
        
        if skills_data.get('technical'):
            categories.append('Technology Trends & Best Practices')
        
        if skills_data.get('industry_specific'):
            categories.append('Industry-Specific Challenges & Solutions')
        
        # Add evergreen topics
        evergreen = [
            'Career Growth & Professional Development',
            'Industry Insights & Future Trends',
            'Project Management Success Stories',
            'Digital Workplace Transformation'
        ]
        
        categories.extend(evergreen)
        
        return list(set(categories))  # Remove duplicates
    
    def generate_content_ideas(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate content ideas based on profile and categories."""
        print(f"\nGenerating {count} content ideas...")
        
        ideas = []
        used_titles = set()
        
        for i in range(count):
            # Select a random category
            category = random.choice(self.topic_categories)
            
            # Generate idea based on category
            idea = self._generate_idea_from_category(category)
            
            # Ensure uniqueness
            if idea['topic'] in used_titles:
                continue
            
            used_titles.add(idea['topic'])
            ideas.append(idea)
        
        # Save ideas
        self._save_content_ideas(ideas)
        self.content_ideas = ideas
        
        print(f"Generated {len(ideas)} unique content ideas")
        return ideas
    
    def _generate_idea_from_category(self, category: str) -> Dict[str, Any]:
        """Generate a content idea from a category."""
        # Topic templates for different categories
        templates = {
            'Pharmaceutical IT & Digital Health': [
                "The Future of Digital Health in Pharma",
                "Navigating Regulatory Challenges in Pharma IT",
                "Success Stories: Digital Transformation in Clinical Trials",
                "AI and Machine Learning in Drug Discovery"
            ],
            'Financial Technology & IT Strategy': [
                "Digital Banking Transformation: Lessons Learned",
                "Cybersecurity Challenges in Financial Services",
                "Blockchain Applications Beyond Cryptocurrency",
                "Data-Driven Decision Making in Finance"
            ],
            'Digital Innovation & Business Transformation': [
                "Leading Digital Transformation: A Practical Guide",
                "Building a Culture of Innovation",
                "Agile Transformation: Success Factors",
                "Measuring ROI on Digital Initiatives"
            ],
            'Leadership & Team Management': [
                "Remote Team Leadership in the Digital Age",
                "Building High-Performance IT Teams",
                "Strategic Thinking for IT Leaders",
                "Mentoring the Next Generation of Tech Leaders"
            ],
            'Technology Trends & Best Practices': [
                "Cloud Migration Strategies That Work",
                "DevOps Best Practices for Enterprise",
                "The Future of Work: Technology Enablers",
                "Sustainable IT: Green Computing Initiatives"
            ]
        }
        
        # Find matching template or use generic
        topic = None
        for cat_key, topic_list in templates.items():
            if cat_key in category:
                topic = random.choice(topic_list)
                break
        
        if not topic:
            topic = f"Insights on {category}"
        
        # Generate key points
        key_points = self._generate_key_points(topic, category)
        
        # Determine content type
        content_types = [ContentType.LINKEDIN_ARTICLE, ContentType.YOUTUBE_SCRIPT, ContentType.BLOG_POST]
        content_type = random.choice(content_types)
        
        idea = {
            'id': f"idea_{hashlib.md5(topic.encode()).hexdigest()[:8]}",
            'topic': topic,
            'category': category,
            'key_points': key_points,
            'content_type': content_type,
            'target_platform': random.choice(self.target_platforms),
            'created_at': datetime.now().isoformat()
        }
        
        return idea
    
    def _generate_key_points(self, topic: str, category: str) -> List[str]:
        """Generate key points for a content idea."""
        key_points = []
        
        # Base key points based on category
        if 'Pharma' in category:
            key_points = [
                "Regulatory compliance considerations",
                "Patient data security and privacy",
                "Integration with existing systems",
                "Measuring clinical outcomes"
            ]
        elif 'Finance' in category:
            key_points = [
                "Risk management and compliance",
                "Customer experience enhancement",
                "Operational efficiency gains",
                "Future-proofing technology investments"
            ]
        elif 'Digital' in category or 'Transformation' in category:
            key_points = [
                "Change management strategies",
                "Technology selection criteria",
                "Stakeholder engagement tactics",
                "Success metrics and KPIs"
            ]
        elif 'Leadership' in category:
            key_points = [
                "Communication strategies",
                "Team motivation techniques",
                "Decision-making frameworks",
                "Professional development planning"
            ]
        else:
            key_points = [
                "Current challenges and opportunities",
                "Best practices and lessons learned",
                "Future trends and predictions",
                "Actionable advice for practitioners"
            ]
        
        # Add 1-2 personalized points based on profile
        profile_skills = self.profile.get('skills', {}).get('detailed', {})
        if profile_skills.get('management'):
            key_points.append("Leadership perspectives from experience")
        if profile_skills.get('technical'):
            key_points.append("Technical implementation insights")
        
        return key_points[:5]  # Limit to 5 key points
    
    def _save_content_ideas(self, ideas: List[Dict[str, Any]]):
        """Save content ideas to file."""
        # Convert enums to strings for JSON serialization
        serializable_ideas = []
        for idea in ideas:
            serializable_idea = idea.copy()
            if isinstance(serializable_idea.get('content_type'), ContentType):
                serializable_idea['content_type'] = serializable_idea['content_type'].value
            serializable_ideas.append(serializable_idea)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ideas_file = os.path.join(self.output_path, "analytics", f"content_ideas_{timestamp}.json")
        
        with open(ideas_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_ideas, f, indent=2, ensure_ascii=False)
        
        print(f"Content ideas saved to: {ideas_file}")
    
    def create_content_draft(self, idea: Dict[str, Any]) -> ContentPiece:
        """Create a content draft from an idea."""
        print(f"\nCreating content draft: {idea['topic']}")
        
        # Generate content based on type
        content_type = idea['content_type']
        content = self._generate_content(idea, content_type)
        
        # Generate tags
        tags = self._generate_tags(idea['topic'], content_type)
        
        # Create content piece
        content_piece = ContentPiece(
            id=f"content_{hashlib.md5(idea['topic'].encode()).hexdigest()[:8]}",
            title=idea['topic'],
            content_type=content_type,
            content=content,
            status=ContentStatus.DRAFT,
            created_at=datetime.now(),
            tags=tags,
            target_platforms=[idea['target_platform']]
        )
        
        # Save draft
        self._save_content_draft(content_piece)
        self.content_pieces.append(content_piece)
        
        print(f"Draft created: {content_piece.id}")
        return content_piece
    
    def _generate_content(self, idea: Dict[str, Any], content_type: ContentType) -> str:
        """Generate content based on type."""
        if content_type == ContentType.LINKEDIN_ARTICLE:
            return self._generate_linkedin_article(idea)
        elif content_type == ContentType.YOUTUBE_SCRIPT:
            return self._generate_youtube_script(idea)
        elif content_type == ContentType.BLOG_POST:
            return self._generate_blog_post(idea)
        else:
            return self._generate_generic_content(idea)
    
    def _generate_linkedin_article(self, idea: Dict[str, Any]) -> str:
        """Generate a LinkedIn article."""
        content = []
        
        # Title
        content.append(f"# {idea['topic']}")
        content.append("")
        
        # Introduction
        content.append("## Introduction")
        content.append(f"In today's rapidly evolving landscape of {idea['category'].lower()}, professionals face new challenges and opportunities. ")
        content.append(f"This article explores key insights and practical advice based on years of industry experience.")
        content.append("")
        
        # Key points as sections
        for i, point in enumerate(idea['key_points'], 1):
            content.append(f"## {point}")
            content.append(f"This is a critical aspect because... [Detailed analysis and insights would go here]. ")
            content.append(f"Based on experience, here are actionable recommendations...")
            content.append("")
        
        # Conclusion
        content.append("## Conclusion")
        content.append(f"{idea['topic']} represents both a challenge and an opportunity. ")
        content.append("By focusing on [key takeaways], professionals can navigate this space successfully.")
        content.append("")
        
        # Call to action
        content.append("**What are your thoughts on this topic? Share your experiences in the comments below!**")
        content.append("")
        content.append("*Connect with me for more insights on [related topics].*")
        
        return "\n".join(content)
    
    def _generate_youtube_script(self, idea: Dict[str, Any]) -> str:
        """Generate a YouTube script."""
        script = []
        
        # Video structure
        sections = [
            "Hook (0-15 seconds)",
            "Introduction & Agenda",
            "Main Content Points", 
            "Examples/Case Studies",
            "Key Takeaways",
            "Call to Action & Subscribe"
        ]
        
        for section in sections:
            script.append(f"## {section}")
            script.append("")
            
            if section == "Hook (0-15 seconds)":
                hooks = [
                    f"Welcome back! Today we're diving deep into {idea['topic'].lower()}.",
                    f"Have you ever struggled with {idea['topic'].lower()}? You're not alone.",
                    f"In this video, I'll share everything I've learned about {idea['topic'].lower()}."
                ]
                script.append(random.choice(hooks))
                
            elif section == "Introduction & Agenda":
                script.append(f"In this video, we'll cover:")
                for i, point in enumerate(idea['key_points'][:3], 1):
                    script.append(f"{i}. {point}")
                script.append("")
                script.append("Whether you're new to this or looking to deepen your knowledge, this video has something for you.")
                
            elif section == "Main Content Points":
                for i, point in enumerate(idea['key_points'], 1):
                    script.append(f"Point {i}: {point}")
                    script.append(f"Explanation: This is crucial because...")
                    script.append("")
                    
            elif section == "Examples/Case Studies":
                script.append("Let me share a real example from my experience:")
                script.append("When I worked with [Company], we faced [Challenge]...")
                script.append("The solution was [Solution], and the results were [Results].")
                script.append("")
                
            elif section == "Key Takeaways":
                script.append("To summarize, here are the key takeaways:")
                for i, point in enumerate(idea['key_points'][:3], 1):
                    script.append(f"{i}. {point}")
                script.append("")
                
            elif section == "Call to Action & Subscribe":
                script.append("If you found this video helpful:")
                script.append("1. Give it a thumbs up 👍")
                script.append("2. Subscribe for more content like this")
                script.append("3. Share it with someone who would benefit")
                script.append("")
                script.append("Leave a comment below with your thoughts or questions!")
            
            script.append("")  # Empty line between sections
        
        return "\n".join(script)
    
    def _generate_blog_post(self, idea: Dict[str, Any]) -> str:
        """Generate a blog post."""
        content = []
        
        # Title and metadata
        content.append(f"# {idea['topic']}")
        content.append("")
        content.append(f"*Published: {datetime.now().strftime('%B %d, %Y')}*")
        content.append(f"*Category: {idea['category']}*")
        content.append("")
        
        # Introduction
        content.append("## Introduction")
        intro_phrases = [
            f"In the dynamic world of {idea['category'].lower()}, staying ahead requires continuous learning and adaptation.",
            f"The landscape of {idea['category'].lower()} is evolving at an unprecedented pace, presenting both challenges and opportunities.",
            f"As professionals in {idea['category'].lower()}, we're constantly navigating new technologies, methodologies, and market demands."
        ]
        content.append(random.choice(intro_phrases))
        content.append(f"This post explores {idea['topic'].lower()} through the lens of practical experience and industry insights.")
        content.append("")
        
        # Main content
        for i, point in enumerate(idea['key_points'], 1):
            content.append(f"## {point}")
            content.append("")
            
            # Generate paragraph for each point
            paragraphs = [
                f"This aspect of {idea['topic'].lower()} is particularly important because it directly impacts [relevant outcome]. In my experience, organizations that prioritize this see measurable improvements in [key metric].",
                f"Many professionals underestimate the complexity of {point.lower()}. However, with the right approach, it can become a significant competitive advantage. The key is to focus on [critical factor] while maintaining flexibility for [changing conditions].",
                f"Successful implementation of {point.lower()} requires a balanced approach. On one hand, you need [technical consideration], and on the other, you must address [organizational factor]. Finding this balance is where true expertise shines."
            ]
            
            for paragraph in paragraphs[:2]:  # 2 paragraphs per point
                content.append(paragraph)
                content.append("")
        
        # Conclusion
        content.append("## Conclusion")
        content.append(f"{idea['topic']} is more than just a trend—it's a fundamental shift in how we approach {idea['category'].lower()}. ")
        content.append("By embracing these principles and adapting them to your specific context, you can achieve [desired outcomes].")
        content.append("")
        
        # Discussion prompts
        content.append("## Discussion Questions")
        content.append("1. How have you approached similar challenges in your organization?")
        content.append("2. What lessons have you learned from implementing these strategies?")
        content.append("3. What future developments do you anticipate in this area?")
        content.append("")
        content.append("*Share your thoughts in the comments below!*")
        
        return "\n".join(content)
    
    def _generate_generic_content(self, idea: Dict[str, Any]) -> str:
        """Generate generic content."""
        return f"# {idea['topic']}\n\nContent about {idea['topic'].lower()} based on professional experience and industry insights."
    
    def _generate_tags(self, topic: str, content_type: ContentType) -> List[str]:
        """Generate relevant tags for content."""
        tags = []
        
        # Topic-based tags
        words = topic.lower().split()
        tags.extend([word for word in words if len(word) > 3][:5])
        
        # Industry tags
        primary_industry = self.profile.get('industries', {}).get('primary', '')
        if primary_industry:
            tags.append(primary_industry.replace('_', ''))
        
        # Content type specific tags
        if content_type == ContentType.LINKEDIN_ARTICLE:
            tags.extend(['thoughtleadership', 'professionaldevelopment', 'careeradvice'])
        elif content_type == ContentType.YOUTUBE_SCRIPT:
            tags.extend(['tutorial', 'howto', 'explainer'])
        elif content_type == ContentType.BLOG_POST:
            tags.extend(['insights', 'analysis', 'industrynews'])
        
        # Skill-based tags
        skills = []
        skills_data = self.profile.get('skills', {}).get('detailed', {})
        for skill_type, skill_list in skills_data.items():
            skills.extend(skill_list[:2])
        
        tags.extend([skill.lower().replace(' ', '') for skill in skills[:3]])
        
        # Remove duplicates and clean
        unique_tags = []
        seen = set()
        for tag in tags:
            clean_tag = re.sub(r'[^a-z0-9]', '', tag.lower())
            if clean_tag and clean_tag not in seen and len(clean_tag) > 2:
                seen.add(clean_tag)
                unique_tags.append(clean_tag)
        
        return unique_tags[:10]
    
    def _save_content_draft(self, content_piece: ContentPiece):
        """Save content draft to file."""
        draft_file = os.path.join(self.output_path, "drafts", f"{content_piece.id}.json")
        
        # Convert to dictionary
        draft_dict = {
            'id': content_piece.id,
            'title': content_piece.title,
            'content_type': content_piece.content_type.value,
            'content': content_piece.content,
            'status': content_piece.status.value,
            'created_at': content_piece.created_at.isoformat(),
            'tags': content_piece.tags,
            'target_platforms': content_piece.target_platforms
        }
        
        with open(draft_file, 'w', encoding='utf-8') as f:
            json.dump(draft_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Draft saved to: {draft_file}")
    
    def review_content(self, content_id: str, feedback: Optional[str] = None) -> ContentPiece:
        """Review content and update status."""
        # Find content piece
        content_piece = None
        for piece in self.content_pieces:
            if piece.id == content_id:
                content_piece = piece
                break
        
        if not content_piece:
            raise ValueError(f"Content piece {content_id} not found")
        
        # Update status based on feedback
        if feedback and "reject" in feedback.lower():
            content_piece.status = ContentStatus.REJECTED
            print(f"Content {content_id} rejected: {feedback}")
        else:
            content_piece.status = ContentStatus.APPROVED
            print(f"Content {content_id} approved")
            
            # Move to approved directory
            self._move_to_approved(content_piece)
        
        return content_piece
    
    def _move_to_approved(self, content_piece: ContentPiece):
        """Move content piece to approved directory."""
        # Source file
        draft_file = os.path.join(self.output_path, "drafts", f"{content_piece.id}.json")
        
        # Destination file
        approved_file = os.path.join(self.output_path, "approved", f"{content_piece.id}.json")
        
        if os.path.exists(draft_file):
            # Update file with new status
            with open(draft_file, 'r', encoding='utf-8') as f:
                draft_data = json.load(f)
            
            draft_data['status'] = content_piece.status.value
            draft_data['reviewed_at'] = datetime.now().isoformat()
            
            with open(approved_file, 'w', encoding='utf-8') as f:
                json.dump(draft_data, f, indent=2, ensure_ascii=False)
            
            # Remove draft file
            os.remove(draft_file)
            
            print(f"Content moved to approved: {approved_file}")
    
    def schedule_content(self, content_id: str, schedule_time: datetime) -> ContentPiece:
        """Schedule content for publication."""
        # Find content piece
        content_piece = None
        for piece in self.content_pieces:
            if piece.id == content_id:
                content_piece = piece
                break
        
        if not content_piece:
            raise ValueError(f"Content piece {content_id} not found")
        
        if content_piece.status != ContentStatus.APPROVED:
            raise ValueError(f"Content must be approved before scheduling")
        
        # Update content piece
        content_piece.status = ContentStatus.SCHEDULED
        content_piece.scheduled_for = schedule_time
        
        # Update file
        self._update_content_schedule(content_piece)
        
        # Add to content calendar
        self._add_to_calendar(content_piece)
        
        print(f"Content {content_id} scheduled for {schedule_time}")
        
        return content_piece
    
    def _update_content_schedule(self, content_piece: ContentPiece):
        """Update content schedule in file."""
        approved_file = os.path.join(self.output_path, "approved", f"{content_piece.id}.json")
        
        if os.path.exists(approved_file):
            with open(approved_file, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            
            content_data['status'] = content_piece.status.value
            content_data['scheduled_for'] = content_piece.scheduled_for.isoformat()
            
            with open(approved_file, 'w', encoding='utf-8') as f:
                json.dump(content_data, f, indent=2, ensure_ascii=False)
    
    def _add_to_calendar(self, content_piece: ContentPiece):
        """Add content to content calendar."""
        calendar_entry = {
            'id': content_piece.id,
            'title': content_piece.title,
            'content_type': content_piece.content_type.value,
            'scheduled_for': content_piece.scheduled_for.isoformat(),
            'platforms': content_piece.target_platforms,
            'status': content_piece.status.value
        }
        
        self.content_calendar.append(calendar_entry)
        
        # Save calendar
        self._save_content_calendar()
    
    def _save_content_calendar(self):
        """Save content calendar to file."""
        calendar_file = os.path.join(self.output_path, "analytics", "content_calendar.json")
        
        with open(calendar_file, 'w', encoding='utf-8') as f:
            json.dump(self.content_calendar, f, indent=2, ensure_ascii=False)
    
    def generate_content_strategy_report(self) -> str:
        """Generate a content strategy report."""
        # Load drafts and approved content
        drafts = self._load_content_from_directory("drafts")
        approved = self._load_content_from_directory("approved")
        
        report = []
        report.append("=" * 80)
        report.append("SOCIAL PROFILE AGENT - CONTENT STRATEGY REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append("CONTENT SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Drafts: {len(drafts)}")
        report.append(f"Approved Content: {len(approved)}")
        report.append(f"Scheduled Content: {len(self.content_calendar)}")
        report.append(f"Primary Industry: {self.profile.get('industries', {}).get('primary', 'N/A').replace('_', ' ').title()}")
        report.append("")
        
        # Content Distribution by Type
        report.append("CONTENT DISTRIBUTION BY TYPE")
        report.append("-" * 40)
        
        type_counts = {}
        for content in drafts + approved:
            if not isinstance(content, dict):
                continue
            content_type = content.get('content_type', 'unknown')
            type_counts[content_type] = type_counts.get(content_type, 0) + 1
        
        for content_type, count in type_counts.items():
            report.append(f"  {content_type}: {count} pieces")
        report.append("")
        
        # Top Topics
        report.append("TOP CONTENT TOPICS")
        report.append("-" * 40)
        
        topics = []
        for content in drafts + approved:
            if not isinstance(content, dict):
                continue
            title = content.get('title', 'Untitled')
            # Extract main topic (first few words)
            topic = ' '.join(title.split()[:5])
            topics.append(topic)
        
        # Count topic frequency
        topic_counts = {}
        for topic in topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            report.append(f"  • {topic} ({count} pieces)")
        report.append("")
        
        # Content Calendar Preview
        report.append("UPCOMING CONTENT SCHEDULE")
        report.append("-" * 40)
        
        if self.content_calendar:
            # Sort by scheduled time
            sorted_calendar = sorted(self.content_calendar, 
                                   key=lambda x: x.get('scheduled_for', ''))
            
            for entry in sorted_calendar[:5]:  # Next 5 scheduled items
                scheduled_time = entry.get('scheduled_for', '')
                if scheduled_time:
                    try:
                        dt = datetime.fromisoformat(scheduled_time)
                        time_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        time_str = scheduled_time
                else:
                    time_str = "Not scheduled"
                
                report.append(f"  {time_str}: {entry.get('title', 'Untitled')}")
                report.append(f"    Type: {entry.get('content_type', 'N/A')}")
                report.append("")
        else:
            report.append("  No content scheduled yet")
            report.append("")
        
        # Recommendations
        report.append("CONTENT STRATEGY RECOMMENDATIONS")
        report.append("-" * 40)
        
        recommendations = [
            "1. Maintain consistent posting schedule (2-3 times per week)",
            "2. Mix content types: Articles (40%), Posts (40%), Videos (20%)",
            "3. Engage with comments to build community",
            "4. Repurpose successful content across platforms",
            "5. Analyze engagement metrics monthly"
        ]
        
        for rec in recommendations:
            report.append(f"  {rec}")
        
        report.append("")
        report.append("=" * 80)
        report.append("Next Steps:")
        report.append("1. Review and approve pending drafts")
        report.append("2. Schedule approved content")
        report.append("3. Monitor engagement and adjust strategy")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def _load_content_from_directory(self, directory: str) -> List[Dict[str, Any]]:
        """Load content from a directory."""
        content_dir = os.path.join(self.output_path, directory)
        content_list = []
        
        if os.path.exists(content_dir):
            for filename in os.listdir(content_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(content_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content_data = json.load(f)
                            content_list.append(content_data)
                    except Exception as e:
                        print(f"Error loading {filepath}: {e}")
        
        return content_list
    
    def run_complete_workflow(self) -> Dict[str, Any]:
        """Run complete content creation workflow."""
        print("\n" + "=" * 60)
        print("Social Profile Agent - Starting Complete Workflow")
        print("=" * 60)
        
        # Step 1: Generate content ideas
        print("\n1. Generating content ideas...")
        ideas = self.generate_content_ideas(count=8)
        print(f"   Generated {len(ideas)} content ideas")
        
        # Step 2: Create drafts from top ideas
        print("\n2. Creating content drafts...")
        drafts = []
        for idea in ideas[:4]:  # Create drafts for top 4 ideas
            draft = self.create_content_draft(idea)
            drafts.append(draft)
            print(f"   Created draft: {draft.title}")
        
        # Step 3: Simulate review process
        print("\n3. Simulating content review...")
        approved = []
        for draft in drafts[:2]:  # Approve first 2 drafts
            approved_draft = self.review_content(draft.id, "Looks good, approved!")
            approved.append(approved_draft)
        
        # Step 4: Schedule approved content
        print("\n4. Scheduling approved content...")
        schedule_time = datetime.now() + timedelta(days=1)
        for content in approved:
            scheduled = self.schedule_content(content.id, schedule_time)
            schedule_time += timedelta(days=2)  # Schedule every 2 days
        
        # Step 5: Generate report
        print("\n5. Generating content strategy report...")
        report = self.generate_content_strategy_report()
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_path, "analytics", f"content_report_{timestamp}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_file}")
        print("\nSocial Profile Agent workflow completed!")
        
        return {
            'ideas_generated': len(ideas),
            'drafts_created': len(drafts),
            'content_approved': len(approved),
            'content_scheduled': len(approved),
            'report_file': report_file,
            'report_preview': report[:500] + "..." if len(report) > 500 else report
        }


def main():
    """Main function to run the Social Profile Agent."""
    print("Career Revolution - Social Profile Agent")
    print("=" * 60)
    
    agent = SocialProfileAgent()
    
    # Run complete workflow
    results = agent.run_complete_workflow()
    
    print(f"\nResults:")
    print(f"  Ideas generated: {results['ideas_generated']}")
    print(f"  Drafts created: {results['drafts_created']}")
    print(f"  Content approved: {results['content_approved']}")
    print(f"  Content scheduled: {results['content_scheduled']}")
    print(f"  Report file: {results['report_file']}")
    
    # Print report preview
    print("\nReport Preview:")
    print("-" * 40)
    print(results['report_preview'])
    
    print("\nSocial Profile Agent completed successfully!")


if __name__ == "__main__":
    main()