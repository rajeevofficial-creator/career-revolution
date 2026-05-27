"""
Setup test environment for Career Revolution agents.
Creates shared_data directory structure and generates sample data for testing.
"""

import os
import json
import shutil
from datetime import datetime, timedelta

def setup_shared_data_structure():
    """Create the complete shared_data directory structure."""
    base_path = "shared_data"
    
    directories = [
        # Profile data
        os.path.join(base_path, "profile"),
        
        # Job data
        os.path.join(base_path, "jobs", "raw"),
        os.path.join(base_path, "jobs", "processed"),
        os.path.join(base_path, "jobs", "recommended"),
        
        # Network data
        os.path.join(base_path, "network", "connections"),
        os.path.join(base_path, "network", "outreach"),
        os.path.join(base_path, "network", "strategies"),
        
        # Application data
        os.path.join(base_path, "applications", "applications"),
        os.path.join(base_path, "applications", "documents"),
        os.path.join(base_path, "applications", "followups"),
        
        # Content data
        os.path.join(base_path, "content", "drafts"),
        os.path.join(base_path, "content", "approved"),
        os.path.join(base_path, "content", "published"),
        
        # Analytics
        os.path.join(base_path, "analytics"),
        
        # Agent orchestrator
        os.path.join(base_path, "orchestrator", "logs"),
        os.path.join(base_path, "orchestrator", "tasks"),
        
        # Analysis
        os.path.join(base_path, "analysis")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created: {directory}")
    
    print(f"\nCreated {len(directories)} directories in {base_path}")

def generate_sample_master_profile():
    """Generate a sample master_profile.json for testing."""
    profile = {
        "summary": {
            "total_documents_analyzed": 302,
            "total_skills_identified": 147,
            "years_experience": 15,
            "highest_education": "master",
            "certification_count": 12,
            "primary_industry": "pharma_it",
            "analysis_date": datetime.now().isoformat()
        },
        "skills": {
            "total_count": 147,
            "by_type": {
                "technical": 45,
                "management": 38,
                "industry_specific": 42,
                "soft_skills": 22
            },
            "detailed": {
                "technical": [
                    "Python", "SQL", "Cloud Computing", "AWS", "Azure",
                    "Docker", "Kubernetes", "DevOps", "CI/CD", "Linux",
                    "Data Analysis", "Big Data", "Cybersecurity", "Networking",
                    "IT Infrastructure", "System Architecture", "API Development"
                ],
                "management": [
                    "Project Management", "Team Leadership", "Strategic Planning",
                    "Budget Management", "Stakeholder Management", "Change Management",
                    "Risk Management", "Process Improvement", "Vendor Management",
                    "Resource Planning", "Performance Management", "Coaching"
                ],
                "industry_specific": [
                    "GMP", "GxP", "Regulatory Compliance", "Clinical Trials",
                    "Pharmacovigilance", "Financial Reporting", "Risk Assessment",
                    "Digital Transformation", "IT Strategy", "Business Intelligence",
                    "ERP", "SAP", "Oracle", "SOX Compliance"
                ],
                "soft_skills": [
                    "Communication", "Presentation", "Negotiation",
                    "Problem Solving", "Critical Thinking", "Adaptability",
                    "Collaboration", "Creativity", "Time Management"
                ]
            }
        },
        "experience": {
            "max_years": 15,
            "avg_years": 12.5,
            "min_years": 8,
            "all_values": [15, 12, 10, 8, 15]
        },
        "education": {
            "highest_level": "master",
            "all_levels": ["master", "bachelor"],
            "count": 5
        },
        "certifications": {
            "total_count": 12,
            "unique_count": 8,
            "by_type": {
                "PMP Certification": 2,
                "ITIL Certification": 2,
                "CGEIT Certification": 1,
                "AWS Certified Solutions Architect": 1,
                "Azure Administrator": 1,
                "Agile Scrum Master": 1,
                "Six Sigma Green Belt": 1,
                "ISO 27001 Lead Auditor": 1
            }
        },
        "industries": {
            "exposure": {
                "pharma_it": 85,
                "finance_it": 45,
                "digital_transformation": 65,
                "consulting": 30,
                "it_services": 25
            },
            "primary": "pharma_it"
        }
    }
    
    profile_path = os.path.join("shared_data", "profile", "master_profile.json")
    with open(profile_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated sample master profile at: {profile_path}")
    return profile_path

def generate_sample_job_recommendations():
    """Generate sample job recommendations."""
    recommendations = [
        {
            "profile_id": "it_director_pharma",
            "title": "IT Director - Pharmaceutical",
            "industry": "Pharmaceutical IT",
            "fit_score": 92.5,
            "skill_gaps": [],
            "match_details": {
                "experience_match": "15y vs 10y required",
                "skills_match": "5/5 skills matched",
                "education_match": "master vs master required",
                "industry_alignment": "pharma_it"
            },
            "location": "Basel, Switzerland",
            "salary_range": "CHF 180,000 - 220,000",
            "description": "Lead IT strategy and digital transformation in pharmaceutical environment."
        },
        {
            "profile_id": "digital_transformation_lead",
            "title": "Digital Transformation Lead",
            "industry": "Digital Transformation",
            "fit_score": 88.3,
            "skill_gaps": ["Missing certifications: Agile, Scrum"],
            "match_details": {
                "experience_match": "15y vs 8y required",
                "skills_match": "4/5 skills matched",
                "education_match": "master vs master required",
                "industry_alignment": "digital_transformation"
            },
            "location": "Zurich, Switzerland",
            "salary_range": "CHF 160,000 - 200,000",
            "description": "Drive digital transformation initiatives across organizations."
        },
        {
            "profile_id": "it_business_partner",
            "title": "IT Business Partner - Finance",
            "industry": "Financial Services IT",
            "fit_score": 85.7,
            "skill_gaps": ["Missing skills: financial reporting"],
            "match_details": {
                "experience_match": "15y vs 7y required",
                "skills_match": "4/5 skills matched",
                "education_match": "master vs bachelor required",
                "industry_alignment": "finance_it"
            },
            "location": "Geneva, Switzerland",
            "salary_range": "CHF 150,000 - 190,000",
            "description": "Bridge IT and finance departments to deliver business value."
        },
        {
            "profile_id": "senior_project_manager",
            "title": "Senior Project Manager",
            "industry": "Consulting",
            "fit_score": 83.2,
            "skill_gaps": ["Missing certifications: Prince2"],
            "match_details": {
                "experience_match": "15y vs 8y required",
                "skills_match": "4/5 skills matched",
                "education_match": "master vs bachelor required",
                "industry_alignment": "consulting"
            },
            "location": "Remote",
            "salary_range": "CHF 140,000 - 180,000",
            "description": "Manage complex projects from initiation to completion."
        },
        {
            "profile_id": "service_delivery_manager",
            "title": "Service Delivery Manager",
            "industry": "IT Services",
            "fit_score": 79.5,
            "skill_gaps": ["Missing certifications: ISO20000"],
            "match_details": {
                "experience_match": "15y vs 6y required",
                "skills_match": "4/5 skills matched",
                "education_match": "master vs bachelor required",
                "industry_alignment": "it_services"
            },
            "location": "Basel, Switzerland",
            "salary_range": "CHF 130,000 - 170,000",
            "description": "Ensure high-quality IT service delivery to clients."
        }
    ]
    
    recommendations_path = os.path.join("shared_data", "jobs", "recommended", "job_recommendations.json")
    with open(recommendations_path, 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)
    
    print(f"Generated sample job recommendations at: {recommendations_path}")
    return recommendations_path

def generate_sample_network_data():
    """Generate sample network data."""
    connections = [
        {
            "id": "conn_001",
            "name": "Dr. Michael Schmidt",
            "title": "CTO - Major Pharma",
            "company": "Major Pharmaceutical Company",
            "industry": "pharma_it",
            "connection_strength": "strong",
            "last_contact": (datetime.now() - timedelta(days=30)).isoformat(),
            "decision_maker": True,
            "budget_owner": True,
            "recommended_action": "Schedule catch-up meeting"
        },
        {
            "id": "conn_002",
            "name": "Sarah Johnson",
            "title": "Head of Digital Transformation",
            "company": "Global Consulting Firm",
            "industry": "digital_transformation",
            "connection_strength": "medium",
            "last_contact": (datetime.now() - timedelta(days=60)).isoformat(),
            "decision_maker": True,
            "budget_owner": False,
            "recommended_action": "Share recent project insights"
        },
        {
            "id": "conn_003",
            "name": "Robert Chen",
            "title": "IT Director - Banking",
            "company": "Swiss Financial Institution",
            "industry": "finance_it",
            "connection_strength": "weak",
            "last_contact": (datetime.now() - timedelta(days=120)).isoformat(),
            "decision_maker": True,
            "budget_owner": True,
            "recommended_action": "Reconnect with industry update"
        },
        {
            "id": "conn_004",
            "name": "Anna Müller",
            "title": "VP IT Services",
            "company": "IT Services Provider",
            "industry": "it_services",
            "connection_strength": "medium",
            "last_contact": (datetime.now() - timedelta(days=45)).isoformat(),
            "decision_maker": True,
            "budget_owner": True,
            "recommended_action": "Discuss potential collaboration"
        },
        {
            "id": "conn_005",
            "name": "David Wilson",
            "title": "Senior Partner",
            "company": "Management Consulting",
            "industry": "consulting",
            "connection_strength": "strong",
            "last_contact": (datetime.now() - timedelta(days=15)).isoformat(),
            "decision_maker": True,
            "budget_owner": True,
            "recommended_action": "Continue regular check-ins"
        }
    ]
    
    connections_path = os.path.join("shared_data", "network", "connections", "linkedin_connections.json")
    with open(connections_path, 'w', encoding='utf-8') as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)
    
    print(f"Generated sample network connections at: {connections_path}")
    return connections_path

def generate_sample_application_data():
    """Generate sample application tracking data."""
    applications = [
        {
            "id": "app_001",
            "job_title": "IT Director - Pharmaceutical",
            "company": "Major Pharma Company",
            "location": "Basel, Switzerland",
            "status": "submitted",
            "submitted_date": (datetime.now() - timedelta(days=7)).isoformat(),
            "follow_up_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "notes": "Strong match with experience and skills"
        },
        {
            "id": "app_002",
            "job_title": "Digital Transformation Lead",
            "company": "Global Consulting Firm",
            "location": "Zurich, Switzerland",
            "status": "under_review",
            "submitted_date": (datetime.now() - timedelta(days=14)).isoformat(),
            "follow_up_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "notes": "Second interview scheduled"
        },
        {
            "id": "app_003",
            "job_title": "IT Business Partner - Finance",
            "company": "Financial Services Leader",
            "location": "Geneva, Switzerland",
            "status": "interview_scheduled",
            "submitted_date": (datetime.now() - timedelta(days=21)).isoformat(),
            "interview_date": (datetime.now() + timedelta(days=5)).isoformat(),
            "notes": "Technical interview with team lead"
        },
        {
            "id": "app_004",
            "job_title": "Senior Project Manager",
            "company": "Tech Consulting",
            "location": "Remote",
            "status": "offer_received",
            "submitted_date": (datetime.now() - timedelta(days=30)).isoformat(),
            "offer_date": (datetime.now() - timedelta(days=2)).isoformat(),
            "notes": "Negotiating salary package"
        },
        {
            "id": "app_005",
            "job_title": "Service Delivery Manager",
            "company": "IT Services Provider",
            "location": "Basel, Switzerland",
            "status": "draft",
            "created_date": datetime.now().isoformat(),
            "notes": "CV customization in progress"
        }
    ]
    
    applications_path = os.path.join("shared_data", "applications", "applications", "applications.json")
    with open(applications_path, 'w', encoding='utf-8') as f:
        json.dump(applications, f, indent=2, ensure_ascii=False)
    
    print(f"Generated sample application data at: {applications_path}")
    return applications_path

def generate_sample_content_data():
    """Generate sample content data."""
    content_ideas = [
        {
            "id": "idea_001",
            "topic": "Digital Transformation in Pharma IT",
            "key_points": [
                "Regulatory challenges in digital transformation",
                "Case study: Successful implementation",
                "Best practices for IT leaders"
            ],
            "target_platform": "linkedin_article",
            "status": "draft"
        },
        {
            "id": "idea_002",
            "topic": "Project Management in Remote Teams",
            "key_points": [
                "Tools for effective remote collaboration",
                "Maintaining team engagement",
                "Measuring productivity remotely"
            ],
            "target_platform": "youtube_script",
            "status": "approved"
        },
        {
            "id": "idea_003",
            "topic": "Career Growth in IT Leadership",
            "key_points": [
                "Skills for future IT leaders",
                "Building strategic influence",
                "Navigating industry changes"
            ],
            "target_platform": "linkedin_article",
            "status": "published"
        }
    ]
    
    content_path = os.path.join("shared_data", "content", "drafts", "content_ideas.json")
    with open(content_path, 'w', encoding='utf-8') as f:
        json.dump(content_ideas, f, indent=2, ensure_ascii=False)
    
    print(f"Generated sample content data at: {content_path}")
    return content_path

def setup_complete_test_environment():
    """Set up complete test environment for all agents."""
    print("=" * 80)
    print("Setting up Career Revolution Test Environment")
    print("=" * 80)
    
    # Create directory structure
    setup_shared_data_structure()
    
    # Generate sample data
    print("\n" + "=" * 80)
    print("Generating Sample Data for Testing")
    print("=" * 80)
    
    profile_path = generate_sample_master_profile()
    job_recs_path = generate_sample_job_recommendations()
    network_path = generate_sample_network_data()
    apps_path = generate_sample_application_data()
    content_path = generate_sample_content_data()
    
    print("\n" + "=" * 80)
    print("Test Environment Setup Complete!")
    print("=" * 80)
    print("\nGenerated files:")
    print(f"1. Master Profile: {profile_path}")
    print(f"2. Job Recommendations: {job_recs_path}")
    print(f"3. Network Connections: {network_path}")
    print(f"4. Applications: {apps_path}")
    print(f"5. Content Ideas: {content_path}")
    print("\nAll agents can now be tested with this sample data.")
    
    return True

if __name__ == "__main__":
    setup_complete_test_environment()