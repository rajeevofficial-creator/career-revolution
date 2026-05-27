# Career Revolution — Features & Functionality

**Version**: Current (as of April 2026)
**Type**: AI-powered career management platform
**Architecture**: FastAPI backend + React frontend + Multi-agent automation

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Authentication & User Management](#authentication--user-management)
4. [Document Management & Intelligence](#document-management--intelligence)
5. [Career Profile Management](#career-profile-management)
6. [Job Search & Discovery Engine](#job-search--discovery-engine)
7. [Job Matching & Recommendations](#job-matching--recommendations)
8. [Automated Application System](#automated-application-system)
9. [LinkedIn Integration](#linkedin-integration)
10. [Interview Preparation](#interview-preparation)
11. [Networking & Relationship Building](#networking--relationship-building)
12. [Professional Brand Building](#professional-brand-building)
13. [Analytics & Dashboard](#analytics--dashboard)
14. [Agent Orchestration System](#agent-orchestration-system)
15. [API Reference](#api-reference)
16. [Data Models](#data-models)
17. [Security](#security)
18. [Third-Party Integrations](#third-party-integrations)
19. [Configuration](#configuration)
20. [Directory Structure](#directory-structure)

---

## Overview

Career Revolution is a full-stack AI-powered career management platform that automates and optimizes the entire job search lifecycle. It combines document intelligence, job discovery, automated applications, interview preparation, and professional networking into a unified system.

**Core capabilities:**
- AI-powered document analysis and career profile extraction
- Automated multi-source job discovery and relevance scoring
- Browser-automated job application submission
- LinkedIn profile analysis and content generation
- Interview preparation with company research
- Professional networking outreach automation

---

## Technology Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.104.1+ with Uvicorn ASGI |
| Database | SQLite (PostgreSQL migration supported) |
| ORM | SQLAlchemy 2.0.23+ |
| Authentication | JWT (OAuth2 Bearer), bcrypt password hashing |
| AI/LLM | Google Generative AI (Gemini 1.5-Flash / 3-Flash) |
| Document Processing | PyPDF2, python-docx, pytesseract, Pillow, pdf2image |
| Web Scraping | BeautifulSoup4, Playwright (browser automation) |
| Search APIs | Serper.dev, Tavily, FireCrawl |
| Encryption | Fernet symmetric encryption (cryptography library) |
| Email | SMTP via Gmail with app passwords |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 18.2.0 |
| UI Library | Material-UI (MUI) 5.14.18 |
| Styling | Emotion (emotion/react, emotion/styled) |
| Forms | react-hook-form 7.48.2 |
| Routing | React Router DOM 6.20.0 |
| HTTP Client | Axios 1.6.2 |
| Notifications | react-toastify 10.0.4 |

---

## Authentication & User Management

### Registration & Login
- Email-based account creation with password hashing (bcrypt)
- JWT token authentication with 30-minute session tokens (configurable)
- Minimum password length: 8 characters

### Email Verification
- Token-based email verification workflow
- Verification email sent via Gmail SMTP
- Admin can manually verify user emails

### Password Management
- Secure password reset via time-limited email tokens
- In-session password change endpoint
- Admin-initiated password reset

### Session Management
- OAuth2 Bearer token scheme
- All protected routes validated via `Depends(get_current_user)`
- Token expiry configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`

---

## Document Management & Intelligence

### Supported File Types
- PDF (`.pdf`)
- Word documents (`.doc`, `.docx`)
- Plain text (`.txt`)
- Images (`.png`, `.jpg`, `.jpeg`)

### Upload Features
- Single file upload
- Batch (multiple file) upload
- Max upload size: 10MB per file (configurable)
- Files stored per-user with unique filenames

### Document Processing (LLM-Powered)
- Automatic skill extraction with category and proficiency levels
- Work experience extraction (company, title, dates, achievements)
- Education extraction (institution, degree, field of study)
- LinkedIn URL detection via regex pattern matching
- Job profile identification — extracts 5–7 ideal job profiles from documents
- Skill gap analysis for target roles
- Processing status tracked per document (`pending`, `processing`, `completed`, `failed`)

### Document Organization
- Categorized by type: resume, certification, portfolio, profile picture
- Folder-level batch analysis (process all docs in a directory at once)
- 302+ sample documents pre-loaded in `jobs_import/` folder with categories:
  - CV, Certifications, Cover Letters, Reference Letters, and 5 more

---

## Career Profile Management

### Profile Fields
- Contact: phone, location, LinkedIn URL, GitHub URL, portfolio URL
- Professional: summary, desired job title, salary expectation, notice period
- Preferences: job types (JSON), work modes (JSON), experience level

### Skills Management
- Add/remove individual skills
- Skill categories: technical, soft, language, certification
- Per-skill: proficiency level, years of experience, confidence score, verification status

### Experience Tracking
- Company, position, location, start/end dates, is_current flag
- Achievement bullet points
- Skills used (JSON array)

### Education Records
- Institution, degree, field of study

### Profile Intelligence
- Profile completion percentage score
- LLM-generated job profile recommendations from uploaded documents
- Skill gap analysis against target roles

---

## Job Search & Discovery Engine

### Job Sources
- **Job Portals**: jobs.ch, Indeed, LinkedIn
- **Company Career Pages**: direct scraping
- **Boutique Recruiters**: specialized recruitment agencies

### Discovery Pipeline (4 Stages)
1. **Query Expansion** — Boolean search query generation from user profile
2. **API Discovery** — Parallel search via Serper, Tavily, and FireCrawl
3. **Triage** — Job validation, deduplication, and categorization
4. **Extraction** — Structured data extraction from job postings

### Search Targeting
- Location-based filtering (Basel, Switzerland + remote)
- Industry focus: Pharma IT, Finance IT
- Seniority-level matching

### Portal Management
- Source database with quality scoring and maturity levels
- Enable/disable individual sources
- Source vetting and validation workflow
- Deduplication across sources

---

## Job Matching & Recommendations

### Relevance Scoring (0–100)
Configurable weighted heuristics:
| Factor | Weight |
|--------|--------|
| Skills match | 20% |
| Description match | 25% |
| Title match | 30% |
| Seniority match | 15% |
| Location match | 15% |
| Industry match | 15% |

### Match Tracking
- All matches stored per user in `job_matches` table
- Score history for comparison over time

### Live Validation
- Periodic checks to verify jobs remain active (`is_live` flag)
- Dead link detection and removal

---

## Automated Application System

### Application Lifecycle
**Statuses**: `draft` → `prepared` → `applied` → `interviewing` → `offered`

### Supported Application Platforms
- LinkedIn Easy Apply
- "Sign in with LinkedIn" portals
- Workday
- Greenhouse
- Lever
- SuccessFactors
- SmartRecruiters
- Generic form-fillers (fallback)

### Automation Features
- Browser automation via Playwright
- Human-like behavior: randomized delays, realistic typing speed
- Stealth headers and user-agent rotation
- CV customization — dynamically generates tailored CV per application
- Cover letter generation — AI-generated and role-specific
- Credential management — encrypted storage of portal logins

### Intervention Handling
System pauses and requests human input for:
- CAPTCHA challenges
- Email verification steps
- Complex or non-standard form fields

### Account Tracking
- Logs new portal accounts created during automation
- Stores credentials encrypted with Fernet

---

## LinkedIn Integration

### URL Extraction
- Regex-based LinkedIn URL detection from uploaded documents
- Bulk extraction across all user documents
- Manual URL override endpoint

### Profile Analysis
- Comprehensive profile scoring
- Optimization recommendations
- LinkedIn status tracking (URL, verification state)

### Content Generation
- Optimized LinkedIn post templates
- Article generation for LinkedIn publishing
- Profile summary improvement suggestions

---

## Interview Preparation

### Company Research
- AI-generated company profiles
- Culture and values analysis
- Recent news and developments

### Question Preparation
- STAR method-based question prediction
- Role-specific question sets
- Likely technical assessment topics

### Mock Interviews
- Simulated interview flow
- Answer evaluation and feedback

### Salary Negotiation
- Market data analysis
- Negotiation strategy generation based on profile and role

### Interviewer Research
- Background analysis on potential interviewers
- LinkedIn-based profile summarization

---

## Networking & Relationship Building

### Connection Analysis
- LinkedIn connection segmentation
- Decision-maker identification (budget owners, hiring managers)

### Outreach Automation
- AI-generated personalized networking messages
- Outreach campaign management
- Follow-up scheduling

### Event Discovery
- Industry conference and meetup identification
- Speaking opportunity research
- Community forum discovery

---

## Professional Brand Building

### Content Generation
- AI-generated articles for LinkedIn and YouTube
- Video scripts for professional content

### Content Calendar
- Schedule and manage content publishing
- Draft → Review → Publish approval workflow

### Platform Optimization
- Content tailored per platform (LinkedIn vs. YouTube)
- Engagement strategy recommendations

---

## Analytics & Dashboard

### User Dashboard
- Profile completion percentage
- Document count by type
- Skills summary
- Recent activity feed

### Application Pipeline View
- All applications grouped by status
- Timeline of status changes
- Application success rate metrics

### Agent Orchestrator Dashboard
- Real-time status of all 6 agents
- Execution times and completion stats
- Error and intervention logs

---

## Agent Orchestration System

Six specialized autonomous agents coordinated by a central orchestrator:

| Agent | Responsibility |
|-------|---------------|
| `job_search_agent` | Job discovery, market intelligence, source management |
| `auto_apply_agent` | Browser-automated application submission |
| `application_tracking_agent` | Application status monitoring and updates |
| `social_profile_agent` | LinkedIn/YouTube content generation |
| `forum_finder_agent` | Event, conference, and community discovery |
| `network_agent` | Relationship mapping and outreach |
| `interview_preparation_agent` | Company research, question prep, mock interviews |
| `agent_orchestrator` | Scheduling, coordination, and monitoring of all agents |

---

## API Reference

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create new user account |
| POST | `/auth/login` | Authenticate and get JWT token |
| POST | `/auth/send-verification-email` | Request verification email |
| GET | `/auth/verify-email` | Complete email verification |
| POST | `/auth/request-password-reset` | Initiate password reset |
| POST | `/auth/reset-password` | Complete password reset |
| POST | `/auth/change-password` | Change current password |

### Profile Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/profile` | Get current user profile |
| PUT | `/profile` | Update profile fields |
| POST | `/profile/skills` | Add a skill |
| DELETE | `/profile/skills/{skill_name}` | Remove a skill |
| PUT | `/profile/experience/{exp_id}` | Update experience entry |
| DELETE | `/profile/experience/{exp_id}` | Delete experience entry |
| PUT | `/profile/education/{edu_id}` | Update education entry |
| DELETE | `/profile/education/{edu_id}` | Delete education entry |
| POST | `/profile/reset` | Reset entire profile |

### Document Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/upload` | Upload single document |
| POST | `/documents/upload-multiple` | Batch upload documents |
| GET | `/documents` | List all user documents |
| GET | `/documents/{document_id}` | Get specific document |
| DELETE | `/documents/{document_id}` | Delete document |
| POST | `/documents/analyze-folder` | Analyze a folder of documents |
| POST | `/documents/analyze-uploaded` | Analyze recently uploaded docs |

### LinkedIn Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/linkedin/extract/{document_id}` | Extract LinkedIn URL from document |
| POST | `/linkedin/extract-all` | Extract from all documents |
| GET | `/linkedin/status` | Get LinkedIn extraction status |
| PUT | `/linkedin/update-url` | Manually set LinkedIn URL |
| POST | `/linkedin/analyze` | Analyze LinkedIn profile |

### Job Search Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/jobs/search` | Search jobs with filters |
| POST | `/jobs/sources/run` | Run job discovery pipeline |
| POST | `/jobs/sources/vet` | Validate job sources |
| GET | `/jobs/sources` | List job sources |
| POST | `/jobs/sources` | Add job source |
| DELETE | `/jobs/sources/{source_id}` | Remove source |
| PATCH | `/jobs/sources/{source_id}/toggle` | Enable/disable source |
| POST | `/jobs/score` | Score job matches for user |

### Application Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/applications` | List all applications |
| POST | `/applications` | Create application |
| POST | `/applications/{id}/prepare` | Generate tailored CV and cover letter |
| POST | `/applications/{id}/apply` | Submit application via automation |
| PATCH | `/applications/{id}` | Update application fields |
| DELETE | `/applications/{id}` | Delete application |
| GET | `/applications/{id}/status` | Get application status |
| POST | `/applications/{id}/intervention` | Provide human intervention data |

### Auto-Apply Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auto-apply/settings` | Get auto-apply configuration |
| POST | `/auto-apply/settings` | Update auto-apply settings |
| GET | `/auto-apply/accounts` | List automation-created accounts |
| POST | `/auto-apply/accounts` | Register new account credentials |

### Analytics Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/social/analysis` | Social profile analysis |
| GET | `/dashboard` | Complete user dashboard data |

### Admin Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List all users (admin only) |
| POST | `/admin/verify-email/{user_id}` | Manually verify user email |
| POST | `/admin/reset-password/{user_id}` | Admin-initiated password reset |

**Total: 70+ endpoints**

---

## Data Models

### Core Tables (12+)

**users**
- `email`, `password_hash`, `full_name`, `is_active`, `is_verified`, `last_login`

**user_profiles**
- `phone`, `location`, `linkedin_url`, `github_url`, `portfolio_url`, `summary`
- `desired_job_title`, `salary_expectation`, `notice_period`
- `job_types` (JSON), `work_modes` (JSON), `experience_level`

**user_documents**
- `document_type`, `original_filename`, `stored_filename`, `file_path`, `file_size`, `mime_type`
- `is_processed`, `processing_status`, `extracted_data` (JSON)

**user_skills**
- `skill_name`, `category`, `proficiency`, `years_experience`, `confidence_score`, `is_verified`

**user_experience**
- `company`, `position`, `location`, `start_date`, `end_date`, `is_current`
- `description`, `achievements`, `skills_used` (JSON)

**user_education**
- Institution, degree, field of study

**verification_tokens**
- Token-based email verification and password reset

**job_sources**
- Portal/company sources with quality scoring and maturity levels

**job_opportunities**
- `title`, `company`, `location`, `description`, `application_url`, `salary_range`
- `skills_required` (JSON), `job_type`, `work_mode`, `experience_level`
- `relevance_score`, `is_live`, `is_verified`

**job_applications**
- `application_url`, `status`, `tailored_cv`, `cover_letter`, `cv_path`, `cl_path`
- `generated_at`, `applied_at`, `intervention_message`, `auto_apply_log` (JSON)

**job_matches**
- User-specific job relevance scores and match history

**auto_apply_credentials**
- Fernet-encrypted portal login credentials

**auto_apply_accounts**
- Accounts created during automation runs

---

## Security

| Feature | Implementation |
|---------|---------------|
| Password hashing | bcrypt with salt |
| Session tokens | JWT signed with SECRET_KEY (HS256) |
| Credential storage | Fernet symmetric encryption |
| SQL injection protection | SQLAlchemy ORM parameterized queries |
| Input validation | Pydantic schemas on all endpoints |
| File upload validation | Type checking + size limits |
| CORS | Configurable (permissive for local dev) |
| Email verification | Token-based with expiry |
| Password reset | Time-limited secure tokens |
| Browser automation stealth | User-agent rotation, realistic timing headers |

---

## Third-Party Integrations

| Service | Purpose |
|---------|---------|
| Google Generative AI (Gemini) | Document analysis, content generation, job matching |
| Serper.dev | Google Search API for job discovery |
| Tavily | Semantic search API for job discovery |
| FireCrawl | Web content extraction from job pages |
| Playwright | Browser automation for job applications |
| Gmail SMTP | Email verification and password reset |
| LinkedIn (scraping) | Profile analysis, job search, Easy Apply |
| Indeed / jobs.ch | Job portal scraping |

---

## Configuration

All configuration via `.env` file:

```env
# Database
DATABASE_URL=sqlite:///./career_revolution.db

# Authentication
SECRET_KEY=<jwt-signing-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (Gmail SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<email>
SMTP_PASSWORD=<app-password>
EMAIL_FROM=<sender-email>

# Application URLs
APP_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# File Storage
UPLOAD_BASE_PATH=uploads
MAX_UPLOAD_SIZE_MB=10

# AI/LLM
GEMINI_API_KEY=<google-generative-ai-key>

# Job Discovery APIs
FIRECRAWL_API_KEY=<firecrawl-key>
SERPER_API_KEY=<serper-key>
TAVILY_API_KEY=<tavily-key>

# Security
CREDENTIAL_ENCRYPTION_KEY=<fernet-key>
```

---

## Directory Structure

```
career_revolution/
├── app/
│   ├── main.py                      # FastAPI app entry point (70+ endpoints)
│   ├── config.py                    # Settings and environment config
│   ├── models/
│   │   ├── database.py              # SQLAlchemy ORM models (12+ tables)
│   │   └── schemas.py               # Pydantic validation schemas (30+)
│   ├── services/                    # Business logic layer (18 services)
│   │   ├── auth.py
│   │   ├── documents.py
│   │   ├── profile.py
│   │   ├── linkedin_service.py
│   │   ├── discovery_engine.py
│   │   ├── document_analysis.py
│   │   ├── llm_analysis.py
│   │   ├── ingestion_service.py
│   │   ├── triage_service.py
│   │   ├── extraction_service.py
│   │   ├── search_service.py
│   │   ├── query_generator.py
│   │   ├── email_service.py
│   │   ├── password_reset.py
│   │   ├── pdf_service.py
│   │   ├── csv_import.py
│   │   └── source_discovery.py
│   ├── utils/
│   │   └── security.py              # Fernet encryption utilities
│   ├── templates/                   # HTML email templates
│   └── api/                         # Route organization (placeholder)
├── agents/                          # Autonomous agent system
│   ├── job_search_agent/
│   │   ├── job_finder_agent.py      # Main discovery pipeline
│   │   └── job_sourcing_agent.py    # Source management
│   ├── auto_apply_agent.py          # Application automation
│   ├── application_tracking_agent/
│   ├── social_profile_agent/        # LinkedIn/YouTube content
│   ├── forum_finder_agent/          # Event discovery
│   ├── network_agent/               # Outreach and networking
│   ├── interview_preparation_agent/
│   └── agent_orchestrator/          # Central coordination + scheduling
├── frontend/                        # React application
│   ├── package.json
│   └── public/src/
├── jobs_import/                     # 302+ career documents
│   ├── CV/
│   ├── Certifications/
│   ├── Cover Letters/
│   ├── Reference Letters/
│   └── (5 more categories)
├── linkedin_analysis_reports/       # Generated analysis output
├── requirements.txt                 # Python dependencies
├── .env                             # Environment configuration
└── career_revolution.db             # SQLite database (~438KB)
```
