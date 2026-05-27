"""
Configuration settings for Career Revolution.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "sqlite:///./career_revolution.db"
    
    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Email (SMTP)
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    email_from: str = os.getenv("EMAIL_FROM", "noreply@career-revolution.com")
    email_from_name: str = os.getenv("EMAIL_FROM_NAME", "Career Revolution")
    
    # App
    app_name: str = "Career Revolution"
    app_url: str = os.getenv("APP_URL", "http://localhost:8000")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost")
    
    # LLM Provider — "gemini" or "claude". Determines which provider all agents use.
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")

    # Gemini AI
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")

    # Anthropic (Claude)
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Discovery & Extraction APIs
    serper_api_key: Optional[str] = os.getenv("SERPER_API_KEY")
    tavily_api_key: Optional[str] = os.getenv("TAVILY_API_KEY")
    firecrawl_api_key: Optional[str] = os.getenv("FIRECRAWL_API_KEY")
    
    # Security
    credential_encryption_key: Optional[str] = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
    
    # File upload
    upload_base_path: str = "uploads"
    max_upload_size_mb: int = 10
    allowed_file_types: list = [".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg"]
    
    class Config:
        env_file = ".env"
        extra = "ignore"

# Create settings instance
settings = Settings()

# Heuristic Discovery Engine Scoring Weights
HEURISTIC_WEIGHTS = {
    "BASE_SCORE": 25,
    "TITLE_MATCH": 30,
    "SENIORITY_MATCH": 15,
    "LOCATION_MATCH": 15,
    "INDUSTRY_MATCH": 15,
    "SKILLS_MATCH": 20,
    "DESCRIPTION_MATCH": 25
}