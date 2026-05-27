"""
Authentication service for Career Revolution.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import os

from app.models.database import User
from app.models.schemas import TokenData, UserCreate

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours — suitable for a full working day

# Use sha256_crypt as fallback if bcrypt has issues
pwd_context = CryptContext(
    schemes=["sha256_crypt", "bcrypt"],
    deprecated="auto",
    sha256_crypt__default_rounds=30000
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(user_data.password)
    
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        created_at=datetime.utcnow(),
        is_verified=False  # New users need to verify email
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create empty profile
    from app.models.database import UserProfile
    profile = UserProfile(user_id=db_user.id)
    db.add(profile)
    db.commit()
    
    # Create and send verification email
    try:
        from app.services.real_email_service import create_verification_token, EmailService
        verification_token = create_verification_token(db, db_user.id)
        
        # Try to send real email
        email_service = EmailService()
        email_sent = email_service.send_verification_email(
            db_user.email, 
            db_user.full_name or db_user.email, 
            verification_token.token
        )
        
        if not email_sent:
            # Fallback to simulated email (for development)
            import logging
            logging.warning(f"Real email not sent for {db_user.email}. Using simulated email.")
            from app.services.email_service import send_verification_email as send_simulated_email
            send_simulated_email(db_user.email, db_user.full_name or db_user.email, verification_token.token)
            
    except Exception as e:
        # Log error but don't fail registration
        import logging
        logging.error(f"Failed to send verification email: {e}")
    
    return db_user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()

def update_user_last_login(db: Session, user_id: int):
    """Update user's last login timestamp."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.last_login = datetime.utcnow()
        db.commit()

def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            return None
        return TokenData(email=email, user_id=user_id)
    except JWTError:
        return None