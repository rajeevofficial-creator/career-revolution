# Career Revolution - Phase 1

## User Management & Profile Upload System

### Overview
Phase 1 implements the foundation of the Career Revolution platform:
- User authentication (register/login)
- Document upload (CVs, certifications, portfolios)
- Profile management
- Secure file storage

### Project Structure
```
career_revolution/
├── app/                    # Application code
│   ├── main.py            # FastAPI application
│   ├── models/            # Database models
│   │   ├── database.py    # SQLAlchemy models
│   │   └── schemas.py     # Pydantic schemas
│   ├── services/          # Business logic
│   │   ├── auth.py        # Authentication service
│   │   ├── documents.py   # Document management
│   │   └── profile.py     # Profile management
│   └── api/               # API routes (to be organized)
├── uploads/               # User uploaded files
├── tests/                 # Test files
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── test_setup.py         # Setup verification
└── README.md             # This file
```

### Features Implemented

#### 1. User Authentication
- Registration with email/password
- Login with JWT tokens
- Password hashing (bcrypt)
- Session management
- Protected routes

#### 2. Document Management
- Upload CVs, certifications, portfolios
- File type validation
- Secure storage organized by user
- Document metadata tracking
- Processing status tracking

#### 3. Profile Management
- Extended user profile
- Contact information
- Career preferences
- Profile completion tracking

#### 4. Database Schema
- Users with authentication
- User profiles
- Document records
- Skills, experience, education (ready for Phase 2)

### API Endpoints

#### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get token

#### Profile
- `GET /profile` - Get user profile
- `PUT /profile` - Update profile

#### Documents
- `POST /documents/upload` - Upload document
- `GET /documents` - List user documents
- `GET /documents/{id}` - Get specific document
- `DELETE /documents/{id}` - Delete document

#### Dashboard
- `GET /dashboard` - User dashboard with all data

### Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Test setup:**
   ```bash
   python test_setup.py
   ```

4. **Run the API:**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Access API documentation:**
   - Open browser to: http://localhost:8000/docs
   - Interactive Swagger UI with all endpoints

### Testing with Sample Data

1. **Register a user:**
   ```bash
   curl -X POST "http://localhost:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "SecurePass123", "full_name": "Test User"}'
   ```

2. **Login:**
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=test@example.com&password=SecurePass123"
   ```

3. **Upload a document:**
   ```bash
   curl -X POST "http://localhost:8000/documents/upload" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "document_type=resume" \
     -F "file=@/path/to/your/resume.pdf"
   ```

### Database Schema Details

#### Users Table
- id, email, password_hash, full_name
- is_active, is_verified, created_at, last_login

#### User Profiles
- user_id, phone, location, linkedin_url
- summary, current_job_title, desired_job_title
- salary_expectation, notice_period

#### User Documents
- user_id, document_type, original_filename
- stored_filename, file_path, file_size
- is_processed, processing_status, extracted_data

#### Ready for Phase 2
- User skills (technical, soft, languages)
- Work experience (companies, positions, dates)
- Education history (institutions, degrees)

### Security Features
- Password hashing with bcrypt
- JWT token authentication
- File type validation
- Secure file storage paths
- SQL injection protection (SQLAlchemy)
- CORS configuration

### Next Steps (Phase 2)

1. **Document Processing**
   - Parse PDF/DOCX resumes
   - Extract skills, experience, education
   - Populate database tables automatically

2. **Job Data Integration**
   - Process "Jobs 2024" folder data
   - Create job matching algorithms
   - Skill gap analysis

3. **Enhanced Features**
   - Profile completion scoring
   - Document processing queue
   - Batch operations

### Development Notes

- Uses SQLite for development (easy to switch to PostgreSQL)
- File uploads stored locally (can be moved to S3/cloud)
- Modular architecture for easy expansion
- Ready for Phase 2 integration

### Troubleshooting

1. **Database issues:**
   - Delete `career_revolution.db` and restart
   - Check SQLite permissions

2. **Import errors:**
   - Ensure you're in the correct directory
   - Check Python path includes project root

3. **File upload issues:**
   - Check uploads directory permissions
   - Verify file size limits in .env

### License
Proprietary - Career Revolution Project