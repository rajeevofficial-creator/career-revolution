# SAMPLE JSON OUTPUTS - What You'll Actually Get

## **1. profile.json** (Complete Consolidated Profile)
```json
{
  "user_id": 1,
  "generated_date": "2026-02-22T21:16:00",
  "document_count": 302,
  "documents_by_type": {
    "cv_resume": 63,
    "certification": 15,
    "reference": 5,
    "cover_letter": 62,
    "other": 157
  },
  "consolidated_data": {
    "personal_info": {
      "name": "Rajeev Sharma",
      "email": "rajeev.sharma@mail.ch",
      "phone": "+41 XX XXX XX XX",
      "location": "Basel, Switzerland",
      "linkedin": "linkedin.com/in/rajeevsharma",
      "work_permit": "Swiss B Permit"
    },
    "skills": [
      "Project Management",
      "IT Governance",
      "ServiceNow",
      "Stakeholder Management",
      "Strategic Planning",
      "Agile Methodology",
      "Scrum",
      "Budget Management",
      "Team Leadership",
      "Risk Management",
      "Digital Transformation",
      "Business Analysis",
      "Process Improvement",
      "Vendor Management",
      "Change Management",
      "German Language (B2)",
      "English Language (Fluent)",
      "Hindi Language (Native)"
    ],
    "experiences": [
      {
        "company": "Infosys Consulting",
        "role": "Senior Project Manager",
        "duration": "2018-2024",
        "location": "Switzerland",
        "achievements": [
          "Led digital transformation projects for pharmaceutical clients",
          "Managed budgets exceeding €2M",
          "Directed teams of 15+ consultants"
        ]
      },
      {
        "company": "Previous Employer",
        "role": "Project Manager",
        "duration": "2015-2018",
        "location": "Switzerland/International",
        "achievements": [
          "Improved process efficiency by 30%",
          "Implemented IT governance frameworks"
        ]
      }
    ],
    "certifications": [
      {
        "name": "Project Management Professional (PMP)",
        "issuer": "Project Management Institute (PMI)",
        "year": "2018",
        "valid_until": "2025"
      },
      {
        "name": "ITIL Foundation",
        "issuer": "AXELOS",
        "year": "2017",
        "valid_until": "Lifetime"
      },
      {
        "name": "CGEIT - Certified in Governance of Enterprise IT",
        "issuer": "ISACA",
        "year": "2019",
        "valid_until": "2024"
      },
      {
        "name": "German Language B2",
        "issuer": "Goethe Institute",
        "year": "2020",
        "valid_until": "N/A"
      }
    ],
    "education": [
      {
        "degree": "Master of Business Administration",
        "institution": "University of XYZ",
        "year": "2010",
        "specialization": "IT Management"
      },
      {
        "degree": "Bachelor of Engineering",
        "institution": "ABC University",
        "year": "2005",
        "specialization": "Computer Science"
      }
    ]
  },
  "source_documents": [
    {
      "filename": "CV-Rajeev Sharma-Oct25.pdf",
      "type": "cv_resume",
      "processing_date": "2026-02-22T21:16:05"
    },
    {
      "filename": "PMP Certificate.pdf",
      "type": "certification",
      "processing_date": "2026-02-22T21:16:10"
    }
  ]
}
```

## **2. extracted/skills.json** (All Skills from All Documents)
```json
[
  {
    "skill": "Project Management",
    "category": "technical",
    "proficiency": "Expert",
    "years_experience": 15,
    "source_documents": ["CV-Rajeev Sharma-Oct25.pdf", "RS-CV Sep 2021.pdf", "CV-IT Finance.pdf"],
    "mentions_count": 58
  },
  {
    "skill": "IT Governance",
    "category": "technical",
    "proficiency": "Advanced",
    "years_experience": 8,
    "source_documents": ["CV-Rajeev Sharma-Oct25.pdf", "CGEIT Certificate.pdf"],
    "mentions_count": 42
  },
  {
    "skill": "ServiceNow",
    "category": "technical",
    "proficiency": "Intermediate",
    "years_experience": 3,
    "source_documents": ["CV-Rajeev Sharma-Oct25.pdf", "RS-CV-Servicenow.pptx"],
    "mentions_count": 35
  },
  {
    "skill": "Stakeholder Management",
    "category": "soft",
    "proficiency": "Expert",
    "source_documents": ["CV-Rajeev Sharma-Oct25.pdf", "Reference Letter Dufry.pdf"],
    "mentions_count": 48
  },
  {
    "skill": "German Language",
    "category": "language",
    "proficiency": "B2",
    "certification": "Goethe B2 Certificate",
    "source_documents": ["German B2 Certificate.pdf", "CV-German version.pdf"],
    "mentions_count": 27
  }
]
```

## **3. extracted/experiences.json** (Work History)
```json
[
  {
    "company": "Infosys Consulting",
    "role": "Senior Project Manager",
    "start_date": "2018",
    "end_date": "2024",
    "location": "Switzerland",
    "is_current": false,
    "description": "Led digital transformation projects for pharmaceutical and financial clients",
    "achievements": [
      "Managed budgets exceeding €2M",
      "Directed teams of 15+ consultants",
      "Implemented IT governance frameworks",
      "Improved operational efficiency by 30%"
    ],
    "skills_used": ["Project Management", "IT Governance", "ServiceNow", "Stakeholder Management"],
    "source_documents": ["CV-Rajeev Sharma-Oct25.pdf", "RS-CV Sep 2021.pdf", "Infosys Reference Letter.pdf"]
  },
  {
    "company": "Previous Employer",
    "role": "Project Manager",
    "start_date": "2015",
    "end_date": "2018",
    "location": "Switzerland/International",
    "is_current": false,
    "description": "Managed IT projects across multiple industries",
    "achievements": [
      "Improved process efficiency by 30%",
      "Implemented compliance systems",
      "Managed cross-functional teams"
    ],
    "skills_used": ["Project Management", "ITIL", "Risk Management", "Team Leadership"],
    "source_documents": ["CV-Rajeev Sharma-Oct25.pdf", "RS-CV Sep 2021.pdf"]
  }
]
```

## **4. extracted/certifications.json** (Certification Details)
```json
[
  {
    "name": "Project Management Professional (PMP)",
    "issuer": "Project Management Institute (PMI)",
    "issue_date": "2018-06",
    "expiry_date": "2025-06",
    "credential_id": "PMP123456",
    "status": "Active",
    "verification_url": "https://verify.pmi.org",
    "source_file": "PMP Certificate.pdf",
    "extracted_data": {
      "certificate_number": "PMP123456",
      "issue_date": "June 2018",
      "expiry_date": "June 2025",
      "pdu_requirements": "60 every 3 years"
    }
  },
  {
    "name": "CGEIT - Certified in Governance of Enterprise IT",
    "issuer": "ISACA",
    "issue_date": "2019-03",
    "expiry_date": "2024-03",
    "credential_id": "CGEIT789012",
    "status": "Needs Renewal",
    "verification_url": "https://verify.isaca.org",
    "source_file": "CGEIT Certificate.pdf",
    "extracted_data": {
      "certificate_number": "CGEIT789012",
      "issue_date": "March 2019",
      "expiry_date": "March 2024"
    }
  },
  {
    "name": "German Language B2",
    "issuer": "Goethe Institute",
    "issue_date": "2020-03",
    "expiry_date": "N/A",
    "credential_id": "B2-2020-1234",
    "status": "Active",
    "source_file": "German B2 Certificate.pdf",
    "extracted_data": {
      "level": "B2",
      "issue_date": "March 2020",
      "score": "85/100"
    }
  }
]
```

## **5. analysis/recommendations.json** (AI Suggestions)
```json
[
  {
    "id": "rec_001",
    "category": "Skill Development",
    "priority": "high",
    "title": "Add Cloud Computing Skills",
    "description": "Add AWS/Azure cloud skills to stay competitive in current market",
    "rationale": "Cloud skills mentioned in only 5% of your documents, but required in 80% of target IT Project Manager roles in Switzerland",
    "action_items": [
      "Complete AWS Cloud Practitioner certification",
      "Take Microsoft Azure Fundamentals course",
      "Add cloud projects to your CV"
    ],
    "timeline": "3-6 months",
    "resources": [
      "AWS Free Tier: https://aws.amazon.com/free",
      "Microsoft Learn: https://learn.microsoft.com",
      "Cloud Guru courses"
    ],
    "impact": "High - Will make you competitive for 80% more roles"
  },
  {
    "id": "rec_002",
    "category": "Certification",
    "priority": "high",
    "title": "Renew PMP Certification",
    "description": "Renew PMP certification before June 2025 expiry",
    "rationale": "PMP is your most valuable certification, mentioned in 45 of your 63 CV versions",
    "action_items": [
      "Earn 60 PDUs before June 2025",
      "Submit renewal application",
      "Pay renewal fee"
    ],
    "timeline": "6 months",
    "resources": [
      "PMI renewal portal: https://www.pmi.org",
      "PDU courses list",
      "Study groups"
    ],
    "impact": "Critical - PMP is essential for senior project management roles"
  },
  {
    "id": "rec_003",
    "category": "Career Advancement",
    "priority": "medium",
    "title": "Target Director-Level Roles",
    "description": "Target Director-level roles in Pharmaceutical IT",
    "rationale": "Your 6+ years pharma experience + PM certifications make you competitive for director roles paying 30-50% more",
    "action_items": [
      "Update LinkedIn headline to \"Senior IT Project Manager | Pharma IT Director Aspirant\"",
      "Network with pharma IT directors on LinkedIn",
      "Apply for 2 director-level roles per month"
    ],
    "timeline": "12-18 months",
    "resources": [
      "LinkedIn Premium for networking",
      "Pharma industry events in Basel",
      "Executive search firms specializing in pharma"
    ],
    "impact": "Medium-High - 30-50% salary increase potential"
  }
]
```

## **6. analysis/statistics.json** (Profile Metrics)
```json
{
  "document_statistics": {
    "total_documents": 302,
    "successfully_processed": 295,
    "failed_documents": 7,
    "success_rate": "97.7%",
    "total_file_size_mb": 145.6,
    "average_document_size_kb": 482
  },
  "profile_statistics": {
    "skills_count": 48,
    "unique_skills": 38,
    "experiences_count": 8,
    "certifications_count": 15,
    "education_entries": 3,
    "languages_count": 3,
    "projects_count": 12
  },
  "quality_metrics": {
    "profile_completeness": 82,
    "data_consistency": 91,
    "document_recency": 78,
    "skill_relevance": 85,
    "market_alignment": 79
  },
  "processing_metrics": {
    "total_processing_time_seconds": 1520,
    "average_processing_time_per_document_seconds": 5.1,
    "text_extraction_accuracy": 87,
    "classification_accuracy": 92,
    "entity_extraction_accuracy": 83
  }
}
```

## **7. documents/index.json** (Document Repository Index)
```json
{
  "cv_resume": [
    {
      "filename": "CV-Rajeev Sharma-Oct25.pdf",
      "file_path": "documents/cv_resume/CV-Rajeev Sharma-Oct25.pdf",
      "file_size_kb": 245,
      "pages": 3,
      "detected_date": "2025-10",
      "version": "Latest",
      "extracted_data": {
        "skills_count": 28,
        "experiences_count": 8,
        "education_count": 2,
        "certifications_count": 4
      },
      "metadata": {
        "creation_date": "2025-10-15",
        "author": "Rajeev Sharma",
        "keywords": ["Project Management", "IT Governance", "Pharmaceutical"]
      }
    },
    {
      "filename": "RS-CV Sep 2021.pdf",
      "file_path": "documents/cv_resume/RS-CV Sep 2021.pdf",
      "file_size_kb": 206,
      "pages": 2,
      "detected_date": "2021-09",
      "version": "Previous",
      "extracted_data": {
        "skills_count": 22,
        "experiences_count": 7,
        "education_count": 2,
        "certifications_count": 3
      }
    }
  ],
  "certifications": [
    {
      "filename": "PMP Certificate.pdf",
      "file_path": "documents/certifications/PMP Certificate.pdf",
      "file_size_kb": 185,
      "certification_name": "Project Management Professional",
      "issuer": "PMI",
      "issue_date": "2018-06",
      "expiry_date": "2025-06",
      "status": "Active"
    },
    {
      "filename": "German B2 Certificate.pdf",
      "file_path": "documents/certifications/German B2 Certificate.pdf",
      "file_size_kb": 320,
      "certification_name": "German Language B2",
      "issuer": "Goethe Institute",
      "issue_date": "2020-03",
      "expiry_date": "N/A",
      "status": "Active"
    }
  ],
  "references": [
    {
      "filename": "Dufry Reference Letter.pdf",
      "file_path": "documents/references/Dufry Reference Letter.pdf",
      "file_size_kb": 150,
      "referrer_name": "John Smith",
      "referrer_position": "Director of IT",
      "referrer_company": "Dufry",
      "reference_date": "2022-05",
      "key_points": ["Leadership", "Project Delivery", "Team Management"]
    }
  ],
  "cover_letters": [
    {
      "filename": "CoverLetter-UBS.docx",
      "file_path": "documents/cover_letters/CoverLetter-UBS.docx",
      "file_size_kb": 45,
      "company": "UBS",
      "position": "IT Project Manager",
      "date": "2023-11",
      "customization_level": "High",
      "key_phrases": ["digital transformation", "regulatory compliance", "stakeholder engagement"]
    }
  ]
}
```

## **8. processing_report.json** (Processing Summary)
```json
{
  "processing_session": {
    "session_id": "proc_20260222_211600",
    "start_time": "2026-02-22T21:16:00",
    "end_time": "2026-02-22T21:41:20",
    "duration_minutes": 25.3,
    "user_id": 1,
    "processor_version": "1.0.0"
  },
  "summary": {
    "total_documents_processed": 302,
    "successfully_processed": 295,
    "failed_documents": 7,
    "success_rate": 97.7,
    "total_extracted_text_chars": 2450000,
    "average_text_per_document_chars": 8305
  },
  "document_types_processed": {
    "cv_resume": {
      "count": 63,
      "success": 62,
      "failed": 1,
      "failed_reasons": ["corrupted_file"]
    },
    "certification": {
      "count": 15,
      "success": 15,
      "failed": 0
    },
    "reference": {
      "count": 5,
      "success": 5,
      "failed": 0
    },
    "cover_letter": {
      "count": 62,
      "success": 60,
      "failed": 2,
      "failed_reasons": ["unsupported_format", "corrupted_file"]
    },
    "other": {
      "count": 157,
      "success": 153,
      "failed": 4,
      "failed_reasons": ["password_protected", "corrupted_file"]
    }
  },
  "extraction_quality": {
    "text_extraction_accuracy": 87.2,
    "classification_accuracy": 92.5,
    "entity_extraction_accuracy": 83.