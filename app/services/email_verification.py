"""
Email Verification Service — verifies job applications via confirmation emails.
"""

import imaplib
import email
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, List

logger = logging.getLogger(__name__)

class EmailVerificationService:
    """Service to poll user's email for job application confirmations."""

    def __init__(self, username: str, password_enc: str):
        self.username = username
        self.password = password_enc # Decrypted by caller
        self.imap_server = self._detect_imap_server(username)

    def _detect_imap_server(self, email_addr: str) -> str:
        """Heuristically detect IMAP server from email domain."""
        domain = email_addr.split("@")[-1].lower()
        if "gmail" in domain:
            return "imap.gmail.com"
        if "outlook" in domain or "hotmail" in domain:
            return "outlook.office365.com"
        if "yahoo" in domain:
            return "imap.mail.yahoo.com"
        if "icloud" in domain:
            return "imap.mail.me.com"
        # Fallback to imap.domain
        return f"imap.{domain}"

    async def verify_confirmation(self, company_name: str, job_title: str, window_minutes: int = 20) -> bool:
        """
        Connect to email and search for a confirmation email.
        Returns True if a match is found.
        """
        if not self.username or not self.password:
            return False

        try:
            # imaplib is blocking, but we run it in a thread if needed. 
            # For simplicity in this agent, we'll run it directly as it's a short check.
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.username, self.password)
            mail.select("inbox")

            # Search criteria: emails received today
            date_since = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE "{date_since}")')
            
            if status != "OK":
                return False

            # Check last 5 emails (most likely to be the one)
            msg_ids = messages[0].split()[-5:]
            for msg_id in reversed(msg_ids):
                status, data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue
                
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                subject = str(msg.get("subject", "")).lower()
                from_addr = str(msg.get("from", "")).lower()
                body = ""
                
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors='ignore').lower()
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore').lower()

                # Check if email is from the company and mentions application
                keywords = ["application", "received", "thank you", "received your interest", "bewerbung"]
                company_match = company_name.lower() in from_addr or company_name.lower() in subject or company_name.lower() in body
                keyword_match = any(k in subject or k in body for k in keywords)
                
                if company_match and keyword_match:
                    logger.info(f"Email confirmation verified for {company_name}")
                    mail.logout()
                    return True

            mail.logout()
        except Exception as e:
            logger.error(f"Email verification failed: {e}")
            
        return False
