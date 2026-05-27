"""
Real email service for Career Revolution.
Uses SMTP to send actual emails.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional
import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import VerificationToken, User

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending real emails via SMTP."""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.email_from = settings.email_from
        self.email_from_name = settings.email_from_name
        self.app_url = settings.app_url
        
    def _create_email_message(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> MIMEMultipart:
        """Create an email message."""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.email_from_name} <{self.email_from}>"
        message["To"] = to_email
        
        # Add HTML part
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Add plain text part if provided
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)
        
        return message
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """
        Send an email via SMTP.
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Email sending disabled.")
            return False
        
        try:
            # Create message
            message = self._create_email_message(to_email, subject, html_content, text_content)
            
            # Create secure SSL context
            context = ssl.create_default_context()
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_verification_email(self, user_email: str, user_name: str, verification_token: str) -> bool:
        """Send email verification email."""
        verification_url = f"{self.app_url}/auth/verify-email?token={verification_token}"
        
        subject = "Verify Your Career Revolution Account"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4361ee 0%, #3a0ca3 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #4361ee; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Career Revolution</h1>
                    <p>AI-Powered Career Portal</p>
                </div>
                <div class="content">
                    <h2>Hello {user_name},</h2>
                    <p>Thank you for registering with Career Revolution!</p>
                    <p>Please verify your email address by clicking the button below:</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </div>
                    
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="background: #eee; padding: 10px; border-radius: 5px; word-break: break-all;">
                        {verification_url}
                    </p>
                    
                    <p>This link will expire in 24 hours.</p>
                    
                    <p>If you didn't create an account, please ignore this email.</p>
                    
                    <p>Best regards,<br>The Career Revolution Team</p>
                </div>
                <div class="footer">
                    <p>© 2026 Career Revolution. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Verify Your Career Revolution Account
        
        Hello {user_name},
        
        Thank you for registering with Career Revolution!
        
        Please verify your email address by clicking the link below:
        
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you didn't create an account, please ignore this email.
        
        Best regards,
        The Career Revolution Team
        """
        
        return self.send_email(user_email, subject, html_content, text_content)
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email after verification."""
        subject = "Welcome to Career Revolution!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4361ee 0%, #3a0ca3 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .feature {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4361ee; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to Career Revolution!</h1>
                </div>
                <div class="content">
                    <h2>Hello {user_name},</h2>
                    <p>Your email has been successfully verified!</p>
                    <p>Welcome to Career Revolution - your AI-powered career portal.</p>
                    
                    <h3>What you can do now:</h3>
                    
                    <div class="feature">
                        <strong>📄 Upload Your Documents</strong>
                        <p>Upload resumes, CVs, certificates, and other career documents.</p>
                    </div>
                    
                    <div class="feature">
                        <strong>🤖 AI-Powered Analysis</strong>
                        <p>Our AI will extract skills, experience, and education from your documents.</p>
                    </div>
                    
                    <div class="feature">
                        <strong>🎯 Personalized Job Matches</strong>
                        <p>Get job recommendations based on your profile and preferences.</p>
                    </div>
                    
                    <div class="feature">
                        <strong>📊 Career Progress Tracking</strong>
                        <p>Track your career growth and skill development over time.</p>
                    </div>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <a href="{self.app_url}" style="background: #4361ee; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Get Started Now
                        </a>
                    </p>
                    
                    <p>Best regards,<br>The Career Revolution Team</p>
                </div>
                <div class="footer">
                    <p>© 2026 Career Revolution. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Career Revolution!
        
        Hello {user_name},
        
        Your email has been successfully verified!
        
        Welcome to Career Revolution - your AI-powered career portal.
        
        You can now:
        1. Upload your resume and documents
        2. Get personalized job matches
        3. Track your career progress
        4. Access career resources
        
        Login to get started: {self.app_url}
        
        Best regards,
        The Career Revolution Team
        """
        
        return self.send_email(user_email, subject, html_content, text_content)

# Helper functions for token management
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