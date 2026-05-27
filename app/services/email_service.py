"""
Email service for Career Revolution.
Simulates email sending for development.
In production, integrate with SendGrid, AWS SES, etc.
"""

import os
import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from app.models.database import VerificationToken, User

logger = logging.getLogger(__name__)

def generate_verification_token(length=32):
    """Generate a random verification token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_verification_token(db: Session, user_id: int, token_type: str = "email_verification", expires_hours: int = 24):
    """Create a verification token for a user."""
    # Delete any existing tokens for this user
    db.query(VerificationToken).filter(
        VerificationToken.user_id == user_id,
        VerificationToken.token_type == token_type,
        VerificationToken.is_used == False
    ).delete()
    
    # Create new token
    token = generate_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
    
    verification_token = VerificationToken(
        user_id=user_id,
        token=token,
        token_type=token_type,
        expires_at=expires_at
    )
    
    db.add(verification_token)
    db.commit()
    db.refresh(verification_token)
    
    return verification_token

def send_verification_email(user_email: str, user_name: str, verification_token: str):
    """
    Simulate sending a verification email.
    In production, this would send an actual email.
    """
    verification_url = f"http://localhost:8000/auth/verify-email?token={verification_token}"
    
    email_content = f"""
    Subject: Verify Your Career Revolution Account
    
    Hello {user_name},
    
    Thank you for registering with Career Revolution!
    
    Please verify your email address by clicking the link below:
    
    {verification_url}
    
    This link will expire in 24 hours.
    
    If you didn't create an account, please ignore this email.
    
    Best regards,
    The Career Revolution Team
    """
    
    # In development, just log the email
    logger.info(f"Verification email would be sent to: {user_email}")
    logger.info(f"Verification URL: {verification_url}")
    # Don't log full email content to avoid encoding issues
    
    # For demo purposes, also print to console
    print("=" * 60)
    print("EMAIL SENT (Development Mode)")
    print("=" * 60)
    print(f"To: {user_email}")
    print(f"Subject: Verify Your Career Revolution Account")
    print(f"Verification URL: {verification_url}")
    print("=" * 60)
    
    return True

def send_welcome_email(user_email: str, user_name: str):
    """Send welcome email after verification."""
    email_content = f"""
    Subject: Welcome to Career Revolution!
    
    Hello {user_name},
    
    Your email has been successfully verified!
    
    Welcome to Career Revolution - your AI-powered career portal.
    
    You can now:
    1. Upload your resume and documents
    2. Get personalized job matches
    3. Track your career progress
    4. Access career resources
    
    Login to get started: http://localhost:3000
    
    Best regards,
    The Career Revolution Team
    """
    
    logger.info(f"Welcome email would be sent to: {user_email}")
    print("=" * 60)
    print("WELCOME EMAIL SENT (Development Mode)")
    print("=" * 60)
    print(f"To: {user_email}")
    print(f"Subject: Welcome to Career Revolution!")
    print("=" * 60)
    
    return True

def verify_token(db: Session, token: str, token_type: str = "email_verification"):
    """Verify a token and mark it as used."""
    verification_token = db.query(VerificationToken).filter(
        VerificationToken.token == token,
        VerificationToken.token_type == token_type,
        VerificationToken.is_used == False,
        VerificationToken.expires_at > datetime.utcnow()
    ).first()
    
    if not verification_token:
        return None
    
    # Mark token as used
    verification_token.is_used = True
    db.commit()
    
    return verification_token

class EmailService:
    """Email service — sends via SMTP when credentials are configured, logs otherwise."""

    def __init__(self):
        import smtplib, ssl
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        self._smtplib = smtplib
        self._ssl = ssl
        self._MIMEText = MIMEText
        self._MIMEMultipart = MIMEMultipart

        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.email_from = os.getenv("EMAIL_FROM", self.smtp_username)
        self.email_from_name = os.getenv("EMAIL_FROM_NAME", "Career Revolution")
        self.smtp_enabled = bool(self.smtp_username and self.smtp_password)

    def _send_smtp(self, to_email: str, subject: str, html_body: str, text_body: str = None) -> bool:
        """Send via SMTP (STARTTLS). Returns True on success."""
        try:
            msg = self._MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.email_from_name} <{self.email_from}>"
            msg["To"] = to_email
            if text_body:
                msg.attach(self._MIMEText(text_body, "plain"))
            msg.attach(self._MIMEText(html_body, "html"))

            ctx = self._ssl.create_default_context()
            with self._smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=ctx)
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"SMTP send failed to {to_email}: {e}")
            return False

    def send_password_reset_email(self, email: str, name: str, reset_link: str, expiry_hours: int = 24) -> bool:
        """Send password reset email."""
        subject = "Reset Your Career Revolution Password"
        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333">
        <div style="max-width:600px;margin:0 auto;padding:20px">
          <div style="background:linear-gradient(135deg,#4361ee,#3a0ca3);color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0">
            <h1 style="margin:0">Career Revolution</h1>
          </div>
          <div style="background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px">
            <h2>Hello {name},</h2>
            <p>We received a request to reset your password.</p>
            <p style="text-align:center">
              <a href="{reset_link}" style="background:#4361ee;color:white;padding:12px 30px;text-decoration:none;border-radius:5px;font-weight:bold;display:inline-block;margin:20px 0">
                Reset My Password
              </a>
            </p>
            <p>Or copy this link into your browser:</p>
            <p style="background:#eee;padding:10px;border-radius:5px;word-break:break-all;font-size:13px">{reset_link}</p>
            <p>This link expires in <strong>{expiry_hours} hours</strong>.</p>
            <p>If you did not request a password reset, you can safely ignore this email.</p>
            <p>Best regards,<br>The Career Revolution Team</p>
          </div>
        </div>
        </body></html>
        """
        text_body = (
            f"Hello {name},\n\nReset your Career Revolution password:\n\n{reset_link}\n\n"
            f"This link expires in {expiry_hours} hours.\n\nIf you didn't request this, ignore this email."
        )

        if self.smtp_enabled:
            return self._send_smtp(email, subject, html_body, text_body)

        # Fallback: log to console so the link is visible during development
        logger.warning("SMTP not configured — printing reset link to console")
        print("=" * 60)
        print("PASSWORD RESET (no SMTP configured)")
        print(f"To: {email}")
        print(f"Reset Link: {reset_link}")
        print("=" * 60)
        return False

    def send_password_changed_confirmation(self, email: str, name: str) -> bool:
        """Send confirmation email when password is changed."""
        subject = "Your Career Revolution Password Has Been Changed"
        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333">
        <div style="max-width:600px;margin:0 auto;padding:20px">
          <div style="background:linear-gradient(135deg,#4361ee,#3a0ca3);color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0">
            <h1 style="margin:0">Career Revolution</h1>
          </div>
          <div style="background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px">
            <h2>Hello {name},</h2>
            <p>Your Career Revolution password was successfully changed.</p>
            <p>If you did not make this change, please contact support immediately.</p>
            <p>Best regards,<br>The Career Revolution Team</p>
          </div>
        </div>
        </body></html>
        """
        text_body = (
            f"Hello {name},\n\nYour Career Revolution password was successfully changed.\n"
            "If you did not make this change, please contact support immediately."
        )

        if self.smtp_enabled:
            return self._send_smtp(email, subject, html_body, text_body)
        return True

    def send_welcome_email(self, email: str, name: str):
        """Send welcome email (wrapper for existing function)."""
        return send_welcome_email(email, name)