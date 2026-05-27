"""
Password reset service for Career Revolution.
Implements industry-standard password recovery flow.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
import re

from app.models.database import User, VerificationToken
from app.services.email_service import EmailService
from app.services.auth import get_password_hash, verify_password

class PasswordResetService:
    """Service for handling password reset requests."""
    
    def __init__(self):
        self.email_service = EmailService()
        self.token_expiry_hours = 24  # Reset tokens expire in 24 hours
        self.min_password_length = 8
        self.password_complexity_rules = {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_digits': True,
            'require_special': False,  # Optional for user convenience
            'max_age_days': 90  # Recommend password change every 90 days
        }
    
    def validate_password_complexity(self, password: str) -> Tuple[bool, str]:
        """Validate password against complexity rules."""
        errors = []
        
        # Check minimum length
        if len(password) < self.password_complexity_rules['min_length']:
            errors.append(f"Password must be at least {self.password_complexity_rules['min_length']} characters")
        
        # Check uppercase
        if self.password_complexity_rules['require_uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Check lowercase
        if self.password_complexity_rules['require_lowercase'] and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Check digits
        if self.password_complexity_rules['require_digits'] and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        # Check special characters (optional)
        if self.password_complexity_rules['require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "Password meets complexity requirements"
    
    def check_password_history(self, db: Session, user_id: int, new_password_hash: str) -> bool:
        """Check if password has been used before (simplified version).
        In production, you would maintain a password history table."""
        # For now, we'll just check against current password
        user = db.query(User).filter(User.id == user_id).first()
        if user and verify_password(new_password_hash, user.password_hash):
            return False  # Password is the same as current
        return True
    
    def generate_reset_token(self) -> str:
        """Generate a secure reset token."""
        return secrets.token_urlsafe(32)
    
    def request_password_reset(self, db: Session, email: str) -> Tuple[bool, str]:
        """Initiate password reset process for a user."""
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Don't reveal whether the email exists — always return success
            return True, "If an account exists with this email, a reset link has been sent"

        # Generate reset token
        token = self.generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)

        # Invalidate any previous unused reset tokens for this user
        db.query(VerificationToken).filter(
            VerificationToken.user_id == user.id,
            VerificationToken.token_type == "password_reset",
            VerificationToken.is_used == False
        ).update({"is_used": True})

        reset_token = VerificationToken(
            user_id=user.id,
            token=token,
            token_type="password_reset",
            expires_at=expires_at,
            is_used=False
        )
        db.add(reset_token)
        db.commit()

        # Build reset link — works when frontend is served from FastAPI or opened as file://
        frontend_base = os.getenv("FRONTEND_URL", "http://localhost:8005/simple_frontend/index.html")
        reset_link = f"{frontend_base}?reset_token={token}"

        email_sent = self.email_service.send_password_reset_email(
            email=user.email,
            name=user.full_name or user.email,
            reset_link=reset_link,
            expiry_hours=self.token_expiry_hours
        )

        if not email_sent:
            print(f"\n{'='*60}")
            print(f"[DEV] Password reset requested for: {user.email}")
            print(f"[DEV] Reset link: {reset_link}")
            print(f"[DEV] Token only: {token}")
            print(f"[DEV] Expires: {expires_at}")
            print(f"{'='*60}\n")

        return True, "If an account exists with this email, a reset link has been sent"
    
    def validate_reset_token(self, db: Session, token: str) -> Tuple[bool, Optional[User], str]:
        """Validate a password reset token."""
        reset_token = db.query(VerificationToken).filter(
            VerificationToken.token == token,
            VerificationToken.token_type == "password_reset",
            VerificationToken.is_used == False,
            VerificationToken.expires_at > datetime.utcnow()
        ).first()
        
        if not reset_token:
            return False, None, "Invalid or expired reset token"
        
        # Get user associated with token
        user = db.query(User).filter(User.id == reset_token.user_id).first()
        if not user:
            return False, None, "User not found"
        
        return True, user, "Token is valid"
    
    def reset_password(self, db: Session, token: str, new_password: str) -> Tuple[bool, str]:
        """Reset password using a valid token."""
        # Validate token
        valid, user, message = self.validate_reset_token(db, token)
        if not valid:
            return False, message
        
        # Validate password complexity
        is_valid, complexity_message = self.validate_password_complexity(new_password)
        if not is_valid:
            return False, complexity_message
        
        # Check password history (simplified)
        new_password_hash = get_password_hash(new_password)
        if not self.check_password_history(db, user.id, new_password):
            return False, "New password cannot be the same as current password"
        
        # Update user password
        user.password_hash = new_password_hash
        user.updated_at = datetime.utcnow()
        
        # Mark token as used
        reset_token = db.query(VerificationToken).filter(
            VerificationToken.token == token,
            VerificationToken.token_type == "password_reset"
        ).first()
        
        if reset_token:
            reset_token.is_used = True
        
        db.commit()
        
        # Send confirmation email
        self.email_service.send_password_changed_confirmation(
            email=user.email,
            name=user.full_name or user.email
        )
        
        return True, "Password has been reset successfully"
    
    def change_password(self, db: Session, user_id: int, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Change password for authenticated user."""
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect"
        
        # Validate new password complexity
        is_valid, complexity_message = self.validate_password_complexity(new_password)
        if not is_valid:
            return False, complexity_message
        
        # Check password history (simplified)
        if verify_password(new_password, user.password_hash):
            return False, "New password cannot be the same as current password"
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        
        # Send confirmation email
        self.email_service.send_password_changed_confirmation(
            email=user.email,
            name=user.full_name or user.email
        )
        
        return True, "Password changed successfully"
    
    def cleanup_expired_tokens(self, db: Session) -> int:
        """Clean up expired password reset tokens."""
        expired_count = db.query(VerificationToken).filter(
            VerificationToken.token_type == "password_reset",
            VerificationToken.expires_at <= datetime.utcnow()
        ).delete()
        
        db.commit()
        return expired_count