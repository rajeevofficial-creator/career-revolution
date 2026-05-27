"""
Forum Finder Agent for Career Revolution
Real-world networking and event discovery agent.
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


class EventType(Enum):
    """Types of networking events."""
    CONFERENCE = "conference"
    MEETUP = "meetup"
    WORKSHOP = "workshop"
    SEMINAR = "seminar"
    WEBINAR = "webinar"
    HACKATHON = "hackathon"
    SPEAKING_OPPORTUNITY = "speaking_opportunity"
    NETWORKING_EVENT = "networking_event"


class EventStatus(Enum):
    """Status of event participation."""
    DISCOVERED = "discovered"
    RECOMMENDED = "recommended"
    REGISTERED = "registered"
    ATTENDED = "attended"
    SPEAKING = "speaking"
    DECLINED = "declined"


class ProposalStatus(Enum):
    """Status of presentation proposals."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class NetworkingEvent:
    """Data class representing a networking event."""
    id: str
    name: str
    event_type: EventType
    description: str
    location: str
    start_date: datetime
    end_date: datetime
    organizer: str
    url: str
    relevance_score: float = 0.0
    status: EventStatus = EventStatus.DISCOVERED
    match_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PresentationProposal:
    """Data class representing a presentation proposal."""
    id: str
    event_id: str
    title: str
    abstract: str
    target_audience: str
    duration_minutes: int
    status: ProposalStatus
    submitted_date: Optional[datetime] = None
    decision_date: Optional[datetime] = None


class ForumFinderAgent:
    """Agent for discovering networking events and creating presentation proposals."""
    
    def __init__(self, profile_data_path: str = "shared_data/profile/master_profile.json",
                 output_path: str = "shared_data/network"):
        """Initialize the forum finder agent."""
        self.profile_data_path = profile_data_path
        self.output_path = output_path
        
        # Load profile data
        self.profile = self._load_profile_data()
        
        # Event data
        self.discovered_events = []
        self.recommended_events = []
        self.presentation_proposals = []
        self.networking_scripts = []
        
        # Event categories based on profile
        self.event_categories = self._generate_event_categories()
        
        # Target locations
        self.target_locations = ["Basel, Switzerland", "Zurich, Switzerland", "Geneva, Switzerland", 
                               "Virtual/Online", "Germany", "France"]
        
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
            os.path.join(self.output_path, "events"),
            os.path.join(self.output_path, "proposals"),
            os.path.join(self.output_path, "scripts"),
            os.path.join(self.output_path, "analytics")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _generate_event_categories(self) -> List[str]:
        """Generate event categories based on profile."""
        categories = []
        
        # Add industry-specific categories
        primary_industry = self.profile.get('industries', {}).get('primary', '')
        if primary_industry:
            industry_map = {
                'pharma_it': 'Pharmaceutical Technology & Digital Health',
                'finance_it': 'FinTech & Financial Services Technology',
                'digital_transformation': 'Digital Innovation & Business Transformation',
                'consulting': 'Management Consulting & Strategy',
                'it_services': 'IT Service Management & Delivery'
            }
            categories.append(industry_map.get(primary_industry, 'Industry Technology'))
        
        # Add skill-based categories
        skills_data = self.profile.get('skills', {}).get('detailed', {})
        
        if skills_data.get('management'):
            categories.append('Leadership & Management')
        
        if skills_data.get('technical'):
            categories.append('Technology & Engineering')
        
        if skills_data.get('industry_specific'):
            categories.append('Industry Regulations & Compliance')
        
        # Add general networking categories
        general = [
            'Professional Networking & Career Development',
            'Innovation & Entrepreneurship',
            'Digital Transformation & Technology Trends',
            'Project Management & Agile Methodologies'
        ]
        
        categories.extend(general)
        
        return list(set(categories))
    
    def discover_events(self, days_ahead: int = 90) -> List[NetworkingEvent]:
        """Discover networking events within the specified timeframe."""
        print(f"\nDiscovering events for next {days_ahead} days...")
        
        # Simulate event discovery
        events = self._simulate_event_discovery(days_ahead)
        
        # Calculate relevance scores
        for event in events:
            event.relevance_score = self._calculate_event_relevance(event)
            event.match_details = self._get_event_match_details(event)
        
        # Sort by relevance
        events.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Save discovered events
        self._save_discovered_events(events)
        self.discovered_events = events
        
        print(f"Discovered {len(events)} events")
        return events
    
    def _simulate_event_discovery(self, days_ahead: int) -> List[NetworkingEvent]:
        """Simulate event discovery (for demo purposes)."""
        events = []
        
        # Event templates
        event_templates = [
            {
                "name": "Pharma IT & Digital Health Conference",
                "type": EventType.CONFERENCE,
                "location": "Basel, Switzerland",
                "organizer": "Pharmaceutical Technology Association",
                "category": "Pharmaceutical Technology & Digital Health",
                "duration_days": 3
            },
            {
                "name": "FinTech Innovation Summit",
                "type": EventType.CONFERENCE,
                "location": "Zurich, Switzerland",
                "organizer": "Swiss Financial Technology Forum",
                "category": "FinTech & Financial Services Technology",
                "duration_days": 2
            },
            {
                "name": "Digital Transformation Leaders Forum",
                "type": EventType.SEMINAR,
                "location": "Virtual/Online",
                "organizer": "Digital Innovation Institute",
                "category": "Digital Innovation & Business Transformation",
                "duration_days": 1
            },
            {
                "name": "IT Leadership Roundtable",
                "type": EventType.MEETUP,
                "location": "Geneva, Switzerland",
                "organizer": "Swiss IT Leadership Network",
                "category": "Leadership & Management",
                "duration_days": 1
            },
            {
                "name": "Cloud & DevOps Workshop",
                "type": EventType.WORKSHOP,
                "location": "Basel, Switzerland",
                "organizer": "Technology Skills Academy",
                "category": "Technology & Engineering",
                "duration_days": 2
            },
            {
                "name": "Regulatory Compliance in Pharma IT",
                "type": EventType.WEBINAR,
                "location": "Virtual/Online",
                "organizer": "Regulatory Affairs Association",
                "category": "Industry Regulations & Compliance",
                "duration_days": 1
            },
            {
                "name": "Project Management Excellence Conference",
                "type": EventType.CONFERENCE,
                "location": "Zurich, Switzerland",
                "organizer": "Project Management Institute",
                "category": "Project Management & Agile Methodologies",
                "duration_days": 2
            },
            {
                "name": "Networking for Tech Leaders",
                "type": EventType.NETWORKING_EVENT,
                "location": "Basel, Switzerland",
                "organizer": "Tech Leadership Community",
                "category": "Professional Networking & Career Development",
                "duration_days": 1
            }
        ]
        
        # Generate events with dates in the future
        base_date = datetime.now()
        
        for i, template in enumerate(event_templates):
            # Random date within the timeframe
            days_offset = random.randint(7, days_ahead)
            start_date = base_date + timedelta(days=days_offset)
            end_date = start_date + timedelta(days=template["duration_days"] - 1)
            
            event = NetworkingEvent(
                id=f"event_{hashlib.md5(template['name'].encode()).hexdigest()[:8]}",
                name=template["name"],
                event_type=template["type"],
                description=f"{template['name']} focusing on {template['category']}. "
                          f"An excellent opportunity for networking and learning.",
                location=template["location"],
                start_date=start_date,
                end_date=end_date,
                organizer=template["organizer"],
                url=f"https://example.com/events/{template['name'].lower().replace(' ', '-')}-{i}",
                status=EventStatus.DISCOVERED
            )
            
            events.append(event)
        
        return events
    
    def _calculate_event_relevance(self, event: NetworkingEvent) -> float:
        """Calculate relevance score for an event."""
        score = 0.0
        
        # 1. Location match (30 points)
        location_score = self._calculate_location_match(event.location)
        score += location_score * 0.30
        
        # 2. Category match (40 points)
        category_score = self._calculate_category_match(event.name, event.description)
        score += category_score * 0.40
        
        # 3. Timing match (20 points)
        timing_score = self._calculate_timing_match(event.start_date, event.end_date)
        score += timing_score * 0.20
        
        # 4. Event type preference (10 points)
        type_score = self._calculate_type_match(event.event_type)
        score += type_score * 0.10
        
        return min(score * 100, 100.0)  # Convert to percentage
    
    def _calculate_location_match(self, location: str) -> float:
        """Calculate location match score."""
        location_lower = location.lower()
        
        # Perfect match for Basel
        if "basel" in location_lower:
            return 1.0
        
        # Good match for Switzerland
        if "switzerland" in location_lower or "suisse" in location_lower or "schweiz" in location_lower:
            return 0.8
        
        # Virtual events
        if "virtual" in location_lower or "online" in location_lower:
            return 0.9
        
        # Other Swiss cities
        swiss_cities = ["zurich", "geneva", "bern", "lausanne", "luzern"]
        for city in swiss_cities:
            if city in location_lower:
                return 0.6
        
        # Nearby countries
        nearby = ["germany", "france", "austria", "italy"]
        for country in nearby:
            if country in location_lower:
                return 0.4
        
        return 0.2
    
    def _calculate_category_match(self, event_name: str, description: str) -> float:
        """Calculate category match score."""
        text = f"{event_name} {description}".lower()
        
        # Check for industry matches
        primary_industry = self.profile.get('industries', {}).get('primary', '')
        
        if primary_industry == 'pharma_it':
            pharma_keywords = ["pharma", "biotech", "medical", "health", "clinical", "regulatory", "gmp", "gxp"]
            for keyword in pharma_keywords:
                if keyword in text:
                    return 1.0
        
        if primary_industry == 'finance_it':
            finance_keywords = ["fintech", "finance", "bank", "insurance", "wealth", "investment", "financial"]
            for keyword in finance_keywords:
                if keyword in text:
                    return 1.0
        
        if primary_industry == 'digital_transformation':
            digital_keywords = ["digital", "transformation", "innovation", "agile", "devops", "cloud", "technology"]
            for keyword in digital_keywords:
                if keyword in text:
                    return 1.0
        
        # Check for skill matches
        skills_data = self.profile.get('skills', {}).get('detailed', {})
        
        if skills_data.get('management'):
            management_keywords = ["leadership", "management", "strategy", "executive", "director"]
            for keyword in management_keywords:
                if keyword in text:
                    return 0.9
        
        if skills_data.get('technical'):
            technical_keywords = ["technology", "engineering", "software", "development", "cloud", "data"]
            for keyword in technical_keywords:
                if keyword in text:
                    return 0.8
        
        # General professional development
        professional_keywords = ["networking", "career", "professional", "development", "workshop", "seminar"]
        for keyword in professional_keywords:
            if keyword in text:
                return 0.7
        
        return 0.4
    
    def _calculate_timing_match(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate timing match score."""
        today = datetime.now()
        days_until = (start_date - today).days
        
        if days_until < 0:
            return 0.0  # Past event
        elif days_until <= 30:
            return 1.0  # Within 30 days - high priority
        elif days_until <= 60:
            return 0.8  # Within 60 days - good timing
        elif days_until <= 90:
            return 0.6  # Within 90 days - reasonable
        else:
            return 0.3  # More than 90 days - low priority
    
    def _calculate_type_match(self, event_type: EventType) -> float:
        """Calculate event type preference score."""
        # Preference order
        preferences = {
            EventType.CONFERENCE: 1.0,  # Best for networking and visibility
            EventType.SEMINAR: 0.9,     # Good for learning and networking
            EventType.WORKSHOP: 0.8,    # Good for skill development
            EventType.WEBINAR: 0.7,     # Convenient but limited networking
            EventType.MEETUP: 0.9,      # Excellent for local networking
            EventType.SPEAKING_OPPORTUNITY: 1.0,  # Best for visibility
            EventType.NETWORKING_EVENT: 0.9,      # Good for connections
            EventType.HACKATHON: 0.6     # Less relevant for leadership roles
        }
        
        return preferences.get(event_type, 0.5)
    
    def _get_event_match_details(self, event: NetworkingEvent) -> Dict[str, Any]:
        """Get detailed match information for an event."""
        details = {
            'location_match': self._calculate_location_match(event.location),
            'category_match': self._calculate_category_match(event.name, event.description),
            'timing_match': self._calculate_timing_match(event.start_date, event.end_date),
            'type_match': self._calculate_type_match(event.event_type),
            'days_until': (event.start_date - datetime.now()).days,
            'duration_days': (event.end_date - event.start_date).days + 1
        }
        
        # Add strengths
        strengths = []
        if details['location_match'] > 0.8:
            strengths.append("Location preference")
        if details['category_match'] > 0.8:
            strengths.append("Industry alignment")
        if details['timing_match'] > 0.8:
            strengths.append("Optimal timing")
        if details['type_match'] > 0.8:
            strengths.append("Preferred event type")
        
        details['strengths'] = strengths
        
        return details
    
    def _save_discovered_events(self, events: List[NetworkingEvent]):
        """Save discovered events to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        events_file = os.path.join(self.output_path, "events", f"discovered_events_{timestamp}.json")
        
        event_dicts = []
        for event in events:
            event_dict = {
                'id': event.id,
                'name': event.name,
                'event_type': event.event_type.value,
                'location': event.location,
                'start_date': event.start_date.isoformat(),
                'end_date': event.end_date.isoformat(),
                'relevance_score': event.relevance_score,
                'status': event.status.value,
                'match_details': event.match_details,
                'url': event.url
            }
            event_dicts.append(event_dict)
        
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(event_dicts, f, indent=2, ensure_ascii=False)
        
        print(f"Discovered events saved to: {events_file}")
    
    def recommend_events(self, min_relevance: float = 70.0, max_events: int = 10) -> List[NetworkingEvent]:
        """Recommend events based on relevance score."""
        if not self.discovered_events:
            print("No events discovered yet. Run discover_events() first.")
            return []
        
        # Filter by relevance
        recommended = [e for e in self.discovered_events if e.relevance_score >= min_relevance]
        
        # Sort by relevance and limit
        recommended.sort(key=lambda x: x.relevance_score, reverse=True)
        recommended = recommended[:max_events]
        
        # Update status
        for event in recommended:
            event.status = EventStatus.RECOMMENDED
        
        # Save recommendations
        self._save_recommended_events(recommended)
        self.recommended_events = recommended
        
        print(f"Recommended {len(recommended)} events (relevance >= {min_relevance}%)")
        return recommended
    
    def _save_recommended_events(self, events: List[NetworkingEvent]):
        """Save recommended events to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        recommendations_file = os.path.join(self.output_path, "events", f"recommended_events_{timestamp}.json")
        
        event_dicts = []
        for event in events:
            event_dict = {
                'id': event.id,
                'name': event.name,
                'event_type': event.event_type.value,
                'location': event.location,
                'start_date': event.start_date.isoformat(),
                'relevance_score': event.relevance_score,
                'status': event.status.value,
                'url': event.url,
                'action': self._generate_event_action(event)
            }
            event_dicts.append(event_dict)
        
        with open(recommendations_file, 'w', encoding='utf-8') as f:
            json.dump(event_dicts, f, indent=2, ensure_ascii=False)
        
        print(f"Recommended events saved to: {recommendations_file}")
    
    def _generate_event_action(self, event: NetworkingEvent) -> str:
        """Generate recommended action for an event."""
        days_until = (event.start_date - datetime.now()).days
        
        if days_until <= 14:
            return "Register immediately - deadline approaching"
        elif days_until <= 30:
            return "Register this week"
        elif days_until <= 60:
            return "Plan attendance - register soon"
        else:
            return "Consider for future planning"
    
    def create_presentation_proposal(self, event_id: str) -> PresentationProposal:
        """Create a presentation proposal for an event."""
        # Find the event
        event = None
        for e in self.recommended_events:
            if e.id == event_id:
                event = e
                break
        
        if not event:
            raise ValueError(f"Event {event_id} not found in recommended events")
        
        print(f"\nCreating presentation proposal for: {event.name}")
        
        # Generate proposal content
        proposal = self._generate_proposal_content(event)
        
        # Save proposal
        self._save_presentation_proposal(proposal)
        self.presentation_proposals.append(proposal)
        
        print(f"Proposal created: {proposal.title}")
        return proposal
    
    def _generate_proposal_content(self, event: NetworkingEvent) -> PresentationProposal:
        """Generate proposal content based on event."""
        # Topic based on event and profile
        primary_industry = self.profile.get('industries', {}).get('primary', '')
        skills_data = self.profile.get('skills', {}).get('detailed', {})
        
        # Generate topic
        topic_templates = {
            'pharma_it': [
                "Digital Transformation in Pharmaceutical IT: Lessons from the Front Lines",
                "Navigating Regulatory Challenges in Pharma Digitalization",
                "AI and Machine Learning Applications in Clinical Trials",
                "Building Agile IT Organizations in Regulated Environments"
            ],
            'finance_it': [
                "FinTech Innovation: Balancing Innovation and Compliance",
                "Digital Banking Transformation: Case Studies and Best Practices",
                "Cybersecurity Strategies for Financial Institutions",
                "Data-Driven Decision Making in Financial Services"
            ],
            'digital_transformation': [
                "Leading Digital Transformation: A Practical Framework",
                "Building a Culture of Innovation in Traditional Organizations",
                "Measuring ROI on Digital Initiatives",
                "Agile Transformation: Beyond the Methodology"
            ]
        }
        
        # Select topic
        topic = None
        if primary_industry in topic_templates:
            topic = random.choice(topic_templates[primary_industry])
        else:
            # Generic topics based on skills
            if skills_data.get('management'):
                topic = "Leadership in Technology: Building High-Performance Teams"
            elif skills_data.get('technical'):
                topic = "Emerging Technology Trends and Their Business Impact"
            else:
                topic = "Professional Insights: Navigating Career Transitions"
        
        # Generate abstract
        abstract = f"This presentation explores {topic.lower()}. "
        abstract += "Drawing from years of hands-on experience, we'll examine real-world case studies, "
        abstract += "discuss practical challenges and solutions, and provide actionable insights for "
        abstract += "professionals navigating similar transformations in their organizations."
        
        # Determine target audience
        audiences = [
            "IT Leaders and Executives",
            "Technology Professionals",
            "Business Transformation Leaders",
            "Project and Program Managers",
            "Industry Practitioners"
        ]
        
        # Create proposal
        proposal = PresentationProposal(
            id=f"proposal_{hashlib.md5(topic.encode()).hexdigest()[:8]}",
            event_id=event.id,
            title=topic,
            abstract=abstract,
            target_audience=random.choice(audiences),
            duration_minutes=random.choice([30, 45, 60]),
            status=ProposalStatus.DRAFT,
            submitted_date=datetime.now()
        )
        
        return proposal
    
    def _save_presentation_proposal(self, proposal: PresentationProposal):
        """Save presentation proposal to file."""
        proposal_file = os.path.join(self.output_path, "proposals", f"{proposal.id}.json")
        
        proposal_dict = {
            'id': proposal.id,
            'event_id': proposal.event_id,
            'title': proposal.title,
            'abstract': proposal.abstract,
            'target_audience': proposal.target_audience,
            'duration_minutes': proposal.duration_minutes,
            'status': proposal.status.value,
            'submitted_date': proposal.submitted_date.isoformat() if proposal.submitted_date else None
        }
        
        with open(proposal_file, 'w', encoding='utf-8') as f:
            json.dump(proposal_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Proposal saved to: {proposal_file}")
    
    def generate_networking_script(self, event_id: str) -> Dict[str, Any]:
        """Generate a networking script for an event."""
        # Find the event
        event = None
        for e in self.recommended_events:
            if e.id == event_id:
                event = e
                break
        
        if not event:
            raise ValueError(f"Event {event_id} not found in recommended events")
        
        print(f"\nGenerating networking script for: {event.name}")
        
        # Generate script
        script = self._generate_networking_script_content(event)
        
        # Save script
        self._save_networking_script(event, script)
        self.networking_scripts.append(script)
        
        print(f"Networking script generated for {event.name}")
        return script
    
    def _generate_networking_script_content(self, event: NetworkingEvent) -> Dict[str, Any]:
        """Generate networking script content."""
        # Event-specific introduction
        introduction = f"I'm attending {event.name} because I'm particularly interested in "
        
        if 'pharma' in event.name.lower() or 'health' in event.name.lower():
            introduction += "the intersection of technology and healthcare, especially how digital transformation is impacting patient outcomes and regulatory compliance."
        elif 'fintech' in event.name.lower() or 'finance' in event.name.lower():
            introduction += "financial technology innovations and how they're reshaping traditional banking and investment services."
        elif 'digital' in event.name.lower() or 'transformation' in event.name.lower():
            introduction += "how organizations are successfully navigating digital transformation challenges and creating sustainable competitive advantages."
        else:
            introduction += "the latest developments in technology leadership and professional networking."
        
        # Conversation starters
        conversation_starters = [
            "What brings you to this event?",
            "What aspect of [event topic] are you most interested in?",
            "Have you attended similar events before? What was your key takeaway?",
            "How is your organization approaching [relevant challenge]?",
            "What's the most interesting development you've seen in our field recently?"
        ]
        
        # Elevator pitch
        primary_industry = self.profile.get('industries', {}).get('primary', '')
        experience = self.profile.get('experience', {}).get('max_years', 10)
        
        elevator_pitch = f"I have over {experience} years of experience in {primary_industry.replace('_', ' ').title() if primary_industry else 'technology leadership'}, "
        elevator_pitch += "focusing on digital transformation, team leadership, and strategic technology implementation. "
        elevator_pitch += "I'm particularly passionate about bridging the gap between business objectives and technical execution."
        
        # Follow-up questions
        follow_up_questions = [
            "What are the biggest challenges you're facing in your current role?",
            "How do you see our industry evolving in the next 3-5 years?",
            "What resources or connections have been most valuable in your career?",
            "Are there any specific projects or initiatives you'd be interested in collaborating on?"
        ]
        
        # Goals for the event
        goals = [
            "Connect with 3-5 industry leaders in my field",
            "Learn about emerging trends and technologies",
            "Identify potential collaboration opportunities",
            "Gain insights for current challenges at work"
        ]
        
        script = {
            'event_id': event.id,
            'event_name': event.name,
            'introduction': introduction,
            'elevator_pitch': elevator_pitch,
            'conversation_starters': conversation_starters,
            'follow_up_questions': follow_up_questions,
            'goals': goals,
            'pre_event_preparation': [
                "Research key speakers and their work",
                "Review latest industry news and developments",
                "Prepare business cards and digital contact information",
                "Set specific networking goals"
            ],
            'post_event_follow_up': [
                "Send personalized connection requests within 24 hours",
                "Reference specific conversations in follow-up messages",
                "Share relevant articles or resources discussed",
                "Schedule follow-up meetings if appropriate"
            ]
        }
        
        return script
    
    def _save_networking_script(self, event: NetworkingEvent, script: Dict[str, Any]):
        """Save networking script to file."""
        script_file = os.path.join(self.output_path, "scripts", f"networking_script_{event.id}.json")
        
        with open(script_file, 'w', encoding='utf-8') as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
        
        print(f"Networking script saved to: {script_file}")
    
    def generate_forum_finder_report(self) -> str:
        """Generate a forum finder report."""
        report = []
        report.append("=" * 80)
        report.append("FORUM FINDER AGENT - NETWORKING STRATEGY REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append("NETWORKING STRATEGY SUMMARY")
        report.append("-" * 40)
        report.append(f"Total events discovered: {len(self.discovered_events)}")
        report.append(f"Highly recommended events: {len(self.recommended_events)}")
        report.append(f"Presentation proposals created: {len(self.presentation_proposals)}")
        report.append(f"Networking scripts generated: {len(self.networking_scripts)}")
        report.append(f"Primary industry focus: {self.profile.get('industries', {}).get('primary', 'N/A').replace('_', ' ').title()}")
        report.append("")
        
        # Top Recommended Events
        report.append("TOP RECOMMENDED EVENTS")
        report.append("-" * 40)
        
        if self.recommended_events:
            for i, event in enumerate(self.recommended_events[:5], 1):
                days_until = (event.start_date - datetime.now()).days
                report.append(f"{i}. {event.name}")
                report.append(f"   Location: {event.location}")
                report.append(f"   Date: {event.start_date.strftime('%Y-%m-%d')} (in {days_until} days)")
                report.append(f"   Type: {event.event_type.value.replace('_', ' ').title()}")
                report.append(f"   Relevance: {event.relevance_score:.1f}%")
                
                if event.match_details.get('strengths'):
                    report.append(f"   Strengths: {', '.join(event.match_details['strengths'][:2])}")
                
                report.append(f"   URL: {event.url}")
                report.append("")
        else:
            report.append("No events recommended yet. Run recommend_events() first.")
            report.append("")
        
        # Presentation Proposals
        report.append("PRESENTATION PROPOSALS")
        report.append("-" * 40)
        
        if self.presentation_proposals:
            for proposal in self.presentation_proposals:
                report.append(f"• {proposal.title}")
                report.append(f"   Duration: {proposal.duration_minutes} minutes")
                report.append(f"   Target: {proposal.target_audience}")
                report.append(f"   Status: {proposal.status.value.title()}")
                report.append("")
        else:
            report.append("No presentation proposals created yet.")
            report.append("")
        
        # Action Plan
        report.append("30-DAY NETWORKING ACTION PLAN")
        report.append("-" * 40)
        
        if self.recommended_events:
            # Get events in next 30 days
            next_30_days = datetime.now() + timedelta(days=30)
            upcoming_events = [e for e in self.recommended_events if e.start_date <= next_30_days]
            
            if upcoming_events:
                report.append("Upcoming Events to Attend:")
                for event in upcoming_events[:3]:
                    days_until = (event.start_date - datetime.now()).days
                    report.append(f"  • {event.name} (in {days_until} days)")
                
                report.append("")
                report.append("Weekly Action Items:")
                report.append("  Week 1: Research events and register")
                report.append("  Week 2: Prepare networking scripts and pitches")
                report.append("  Week 3: Attend events and network actively")
                report.append("  Week 4: Follow up with connections")
            else:
                report.append("No highly relevant events in next 30 days.")
                report.append("Consider expanding search criteria or looking at virtual events.")
        else:
            report.append("No events to plan for. Discover events first.")
        
        report.append("")
        report.append("=" * 80)
        report.append("Next Steps:")
        report.append("1. Register for top recommended events")
        report.append("2. Create presentation proposals for speaking opportunities")
        report.append("3. Prepare networking scripts for each event")
        report.append("4. Schedule follow-up activities")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run_complete_workflow(self) -> Dict[str, Any]:
        """Run complete forum finder workflow."""
        print("\n" + "=" * 60)
        print("Forum Finder Agent - Starting Complete Workflow")
        print("=" * 60)
        
        # Step 1: Discover events
        print("\n1. Discovering events...")
        events = self.discover_events(days_ahead=90)
        print(f"   Discovered {len(events)} events")
        
        # Step 2: Recommend events
        print("\n2. Recommending events...")
        recommended = self.recommend_events(min_relevance=70, max_events=8)
        print(f"   Recommended {len(recommended)} events")
        
        # Step 3: Create presentation proposals
        print("\n3. Creating presentation proposals...")
        proposals = []
        if recommended:
            for event in recommended[:2]:  # Create proposals for top 2 events
                proposal = self.create_presentation_proposal(event.id)
                proposals.append(proposal)
                print(f"   Created proposal: {proposal.title}")
        
        # Step 4: Generate networking scripts
        print("\n4. Generating networking scripts...")
        scripts = []
        if recommended:
            for event in recommended[:2]:  # Create scripts for top 2 events
                script = self.generate_networking_script(event.id)
                scripts.append(script)
                print(f"   Generated script for: {event.name}")
        
        # Step 5: Generate report
        print("\n5. Generating forum finder report...")
        report = self.generate_forum_finder_report()
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_path, "analytics", f"forum_finder_report_{timestamp}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_file}")
        print("\nForum Finder Agent workflow completed!")
        
        return {
            'events_discovered': len(events),
            'events_recommended': len(recommended),
            'proposals_created': len(proposals),
            'scripts_generated': len(scripts),
            'report_file': report_file,
            'report_preview': report[:500] + "..." if len(report) > 500 else report
        }


def main():
    """Main function to run the Forum Finder Agent."""
    print("Career Revolution - Forum Finder Agent")
    print("=" * 60)
    
    agent = ForumFinderAgent()
    
    # Run complete workflow
    results = agent.run_complete_workflow()
    
    print(f"\nResults:")
    print(f"  Events discovered: {results['events_discovered']}")
    print(f"  Events recommended: {results['events_recommended']}")
    print(f"  Proposals created: {results['proposals_created']}")
    print(f"  Scripts generated: {results['scripts_generated']}")
    print(f"  Report file: {results['report_file']}")
    
    # Print report preview
    print("\nReport Preview:")
    print("-" * 40)
    print(results['report_preview'])
    
    print("\nForum Finder Agent completed successfully!")


if __name__ == "__main__":
    main()