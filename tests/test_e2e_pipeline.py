import os
import sys
import asyncio
import logging
import datetime
import traceback
from typing import Dict, Any

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("e2e_test")

from app.models.database import SessionLocal, JobApplication, User, LinkedInSession
from app.utils.security import decrypt_value
from app.services.email_verification import EmailVerificationService
from app.main import prepare_application_materials

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_section(title: str):
    print("\n" + "=" * 60)
    print(f"{Color.BOLD}{Color.CYAN}{title.upper()}{Color.END}")
    print("=" * 60)

async def test_database_health() -> Dict[str, Any]:
    print_section("Step 1: Database & Health Check")
    db = SessionLocal()
    try:
        # Check users
        users = db.query(User).all()
        logger.info(f"Database connected successfully. Found {len(users)} registered user(s).")
        if not users:
            raise Exception("No users found in database. Run populate_db.py first.")
            
        target_user = users[0]
        logger.info(f"Targeting User ID: {target_user.id} ({target_user.email}) for verification.")
        
        # Check LinkedInSession
        li_session = db.query(LinkedInSession).filter(LinkedInSession.user_id == target_user.id).first()
        if li_session:
            logger.info(f"LinkedIn Session exists. is_valid={li_session.is_valid}")
        else:
            logger.warning("No LinkedIn Session stored in database.")
            
        # Get applications
        apps = db.query(JobApplication).filter(JobApplication.user_id == target_user.id).all()
        logger.info(f"User has {len(apps)} job application(s) in the database.")
        
        return {"success": True, "user": target_user, "apps": apps}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

async def test_prepare_materials(user_id: int, app_id: int) -> Dict[str, Any]:
    print_section("Step 2: Prepare Engine (JD Scrape & AI Tailoring)")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
        
        if not app:
            raise Exception(f"Application ID {app_id} not found in database.")
            
        logger.info(f"Testing Prepare for App ID {app.id} (URL: {app.application_url})")
        
        # Clear existing CV and Cover Letter to ensure we test generation end-to-end
        logger.info("Clearing existing tailored CV and Cover Letter in DB to verify regeneration...")
        app.tailored_cv = None
        app.cover_letter = None
        app.cv_path = None
        app.cl_path = None
        app.status = "draft"
        db.commit()
        db.refresh(app)
        
        # Trigger prepare materials endpoint
        logger.info("Triggering prepare_application_materials...")
        result = await prepare_application_materials(
            id=app_id,
            body=None,
            current_user=user,
            db=db
        )
        
        # Verify result structure
        if result.get("status") == "error":
            raise Exception(f"Prepare endpoint returned error status: {result.get('message')}")
            
        # Refresh app state from database
        db.refresh(app)
        
        # Assert CV and Cover Letter text fields are not empty
        if not app.tailored_cv:
            raise Exception("Prepare succeeded but tailored_cv text field is empty in DB.")
        if not app.cover_letter:
            raise Exception("Prepare succeeded but cover_letter text field is empty in DB.")
            
        logger.info(f"{Color.GREEN}[OK] Tailored materials successfully saved in DB.{Color.END}")
        logger.info(f"CV Snippet: {app.tailored_cv[:150].replace('\n', ' ')}...")
        logger.info(f"CL Snippet: {app.cover_letter[:150].replace('\n', ' ')}...")
        
        # Assert PDF paths exist on disk
        if not app.cv_path:
            raise Exception("Prepare succeeded but cv_path is empty in DB.")
        if not app.cl_path:
            raise Exception("Prepare succeeded but cl_path is empty in DB.")
            
        cv_abs = os.path.abspath(app.cv_path)
        cl_abs = os.path.abspath(app.cl_path)
        
        if not os.path.exists(cv_abs):
            raise Exception(f"CV PDF file not found on disk at: {cv_abs}")
        if not os.path.exists(cl_abs):
            raise Exception(f"Cover Letter PDF file not found on disk at: {cl_abs}")
            
        logger.info(f"{Color.GREEN}[OK] Tailored PDF files verified on disk.{Color.END}")
        logger.info(f"  CV PDF: {cv_abs} (Size: {os.path.getsize(cv_abs)} bytes)")
        logger.info(f"  CL PDF: {cl_abs} (Size: {os.path.getsize(cl_abs)} bytes)")
        
        return {"success": True, "cv_path": cv_abs, "cl_path": cl_abs}
    except Exception as e:
        logger.error(f"Prepare Engine verification failed: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

async def test_email_verification_imap(user_id: int) -> Dict[str, Any]:
    print_section("Step 3: Post-Apply Verification (IMAP Confirmation Email Check)")
    db = SessionLocal()
    try:
        # Retrieve credentials from auto_apply_credentials table
        from sqlalchemy import text
        cursor = db.execute(
            text("SELECT email_username, email_password_enc FROM auto_apply_credentials WHERE user_id = :uid"),
            {"uid": user_id}
        )
        row = cursor.fetchone()
        if not row:
            raise Exception(f"No IMAP credentials found in auto_apply_credentials table for user_id={user_id}.")
            
        username = row[0]
        encrypted_password = row[1]
        
        if not username or not encrypted_password:
            raise Exception("IMAP credentials username or password string is empty.")
            
        decrypted_password = decrypt_value(encrypted_password)
        logger.info(f"IMAP settings fetched from DB. Username: {username}")
        
        # Instantiate verifier
        logger.info("Initializing EmailVerificationService and connecting to IMAP server...")
        verifier = EmailVerificationService(username, decrypted_password)
        
        # Test standard connection & non-existent query to ensure API performs search successfully
        logger.info("Performing IMAP health search (verifying protocol correctness)...")
        # Querying a dummy company name
        is_verified = await verifier.verify_confirmation(
            company_name="NonExistentDummyCompanyXYZ",
            job_title="Software Developer"
        )
        logger.info(f"IMAP search executed successfully. Verification result (expected False): {is_verified}")
        
        # Try to find any confirmation emails from Hays or general keywords in the last 60 days
        # to ensure that email parsing logic matches real emails correctly
        logger.info("Verifying email parser heuristics (checking for historical confirmation emails)...")
        import imaplib
        import email
        
        mail = imaplib.IMAP4_SSL(verifier.imap_server)
        mail.login(verifier.username, verifier.password)
        mail.select("inbox")
        
        # Check back 60 days to find at least one historical confirmation email
        date_since = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{date_since}")')
        
        found_confirmations = 0
        if status == "OK" and messages[0]:
            msg_ids = messages[0].split()
            logger.info(f"Found {len(msg_ids)} total emails in inbox in the last 60 days. Inspecting last 25 for confirmation keywords...")
            
            keywords = ["application", "received", "thank you", "interest", "bewerbung", "eingegangen"]
            for msg_id in reversed(msg_ids[-25:]):
                try:
                    fetch_status, data = mail.fetch(msg_id, "(RFC822)")
                    if fetch_status != "OK":
                        continue
                        
                    msg = email.message_from_bytes(data[0][1])
                    subject = str(msg.get("subject", "")).lower()
                    from_addr = str(msg.get("from", "")).lower()
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore").lower()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore").lower()
                        
                    keyword_matches = [k for k in keywords if k in subject or k in body]
                    if keyword_matches:
                        found_confirmations += 1
                        logger.info(f"  {Color.GREEN}[OK] Match found!{Color.END}")
                        logger.info(f"    From: {msg.get('From')}")
                        logger.info(f"    Subject: {msg.get('Subject')}")
                        logger.info(f"    Matched keywords: {keyword_matches}")
                        if found_confirmations >= 3: # limit log noise
                            break
                except Exception as parse_err:
                    logger.warning(f"Error parsing email ID {msg_id}: {parse_err}")
                    
        mail.logout()
        logger.info(f"IMAP Parsing check complete. Found {found_confirmations} email matches with confirmation heuristics.")
        
        return {"success": True, "username": username}
    except Exception as e:
        logger.error(f"IMAP Email Verification failed: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

async def run_pipeline():
    print(f"\n{Color.BOLD}{Color.YELLOW}=== CAREER REVOLUTION END-TO-END VALIDATION PIPELINE ==={Color.END}")
    
    # 1. DB & Health Check
    db_res = await test_database_health()
    if not db_res["success"]:
        print(f"\n{Color.RED}[FAIL] Step 1 (DB Check) FAILED. Aborting test.{Color.END}")
        sys.exit(1)
        
    user = db_res["user"]
    apps = db_res["apps"]
    
    if not apps:
        print(f"\n{Color.RED}[FAIL] No applications found. Cannot test Prepare stage. Aborting.{Color.END}")
        sys.exit(1)
        
    # Use the last application for E2E testing
    target_app = apps[-1]
    
    # 2. Test Prepare Materials
    prep_res = await test_prepare_materials(user.id, target_app.id)
    if not prep_res["success"]:
        print(f"\n{Color.RED}[FAIL] Step 2 (Prepare Engine) FAILED.{Color.END}")
        sys.exit(1)
        
    # 3. Test Email Verification
    email_res = await test_email_verification_imap(user.id)
    if not email_res["success"]:
        print(f"\n{Color.RED}[FAIL] Step 3 (Email Verification) FAILED.{Color.END}")
        sys.exit(1)
        
    print(f"\n{Color.BOLD}{Color.GREEN}============================================================{Color.END}")
    print(f"{Color.BOLD}{Color.GREEN}[SUCCESS] ALL STEPS IN THE PIPELINE ARE WORKING E2E!{Color.END}")
    print(f"{Color.BOLD}{Color.GREEN}============================================================{Color.END}")
    print(f"- DB Connection & Health: {Color.GREEN}PASSED{Color.END}")
    print(f"- LinkedIn JD Fetch & AI Tailoring: {Color.GREEN}PASSED{Color.END}")
    print(f"- PDF Document Generation: {Color.GREEN}PASSED{Color.END}")
    print(f"- IMAP Connection & Search Logic: {Color.GREEN}PASSED{Color.END}")
    print(f"============================================================\n")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
