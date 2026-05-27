# Career Revolution - Phase 1 Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy the example environment file
copy .env.example .env

# Edit .env with your settings (optional for development)
# For quick testing, you can use defaults
```

### 3. Run the API
```bash
python run.py
```

### 4. Access API Documentation
Open your browser to: http://localhost:8000/docs

## Project Structure Created

```
career_revolution/
├── app/                    # Main application
│   ├── main.py            # FastAPI app with all endpoints
│   ├── models/
│   │   ├── database.py    # SQLAlchemy models (6 tables)
│   │   └── schemas.py     # Pydantic schemas (15+ models)
│   └── services/
│       ├── auth.py        # Authentication with JWT
│       ├── documents.py   # File upload management
│       └── profile.py     # Profile CRUD operations
├── uploads/               # User file storage
├── requirements.txt       # 12+ Python packages
├── run.py                # Easy startup script
└── README.md             # Complete documentation
```

## What's Implemented (Phase 1)

### ✅ Core Features
1. **User Authentication**
   - Registration with email/password
   - Login with JWT tokens
   - Password hashing (bcrypt)
   - Protected API routes

2. **Document Management**
   - Upload CVs, certifications, portfolios
   - File validation and secure storage
   - Document metadata tracking
   - Processing status system

3. **Profile Management**
   - Extended user profiles
   - Career preferences
   - Contact information
   - Profile completion tracking

4. **Database Ready**
   - 6 normalized tables
   - Relationships between entities
   - Ready for Phase 2 data extraction

### ✅ API Endpoints
- `POST /auth/register` - User registration
- `POST /auth/login` - User login (returns JWT)
- `GET /profile` - Get user profile
- `PUT /profile` - Update profile
- `POST /documents/upload` - Upload files
- `GET /documents` - List user documents
- `GET /dashboard` - Complete user dashboard

### ✅ Security Features
- Password hashing with bcrypt
- JWT token authentication
- File type/size validation
- SQL injection protection
- CORS configuration

## Testing the API

### 1. Register a User
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123",
    "full_name": "Test User"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=SecurePass123"
```
Save the `access_token` from the response.

### 3. Upload a Document
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "document_type=resume" \
  -F "file=@C:\path\to\your\resume.pdf"
```

### 4. View Dashboard
```bash
curl -X GET "http://localhost:8000/dashboard" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Database Schema

### Users Table
- `id`, `email`, `password_hash`, `full_name`
- `is_active`, `is_verified`, `created_at`, `last_login`

### User Profiles
- `user_id`, `phone`, `location`, `linkedin_url`
- `summary`, `current_job_title`, `desired_job_title`
- `salary_expectation`, `notice_period`

### User Documents
- `user_id`, `document_type`, `original_filename`
- `stored_filename`, `file_path`, `file_size`
- `is_processed`, `processing_status`, `extracted_data`

### Ready for Phase 2
- `user_skills` - Technical/soft skills
- `user_experience` - Work history
- `user_education` - Education background

## Next Steps (Phase 2)

### Document Processing Pipeline
1. Parse uploaded documents (PDF/DOCX)
2. Extract skills, experience, education
3. Auto-populate database tables
4. Create structured profile from documents

### Job Data Integration
1. Process "Jobs 2024" folder data
2. Create job matching algorithms
3. Implement skill gap analysis
4. Build job recommendation engine

### Enhanced Features
1. Profile completion scoring
2. Document processing queue
3. Batch operations
4. Advanced search/filtering

## Development Notes

- **Database**: SQLite for development (easy PostgreSQL migration)
- **File Storage**: Local filesystem (ready for S3/cloud)
- **Architecture**: Modular, scalable design
- **API**: Fully documented with Swagger UI

## Troubleshooting

### Common Issues
1. **Import errors**: Make sure you're in the `career_revolution` directory
2. **Database issues**: Delete `career_revolution.db` and restart
3. **Port conflicts**: Change port in `run.py` (default: 8000)
4. **File upload errors**: Check `uploads/` directory permissions

### Quick Fixes
```bash
# Recreate database
del career_revolution.db
python run.py

# Check dependencies
pip list | findstr fastapi

# Test API directly
curl http://localhost:8000/
```

## Ready for Development

The Phase 1 foundation is complete and ready for:
1. Testing with real user data
2. Integration with "Jobs 2024" folder
3. Phase 2 document processing development
4. Frontend development (React/Next.js)

**API Documentation**: http://localhost:8000/docs (after starting server)