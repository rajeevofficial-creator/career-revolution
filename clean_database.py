"""
Clean database for fresh email verification test.
Keeps only rajeev.sharma@mail.ch account.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.database import SessionLocal, User, VerificationToken, UserProfile, UserDocument, UserSkill, UserExperience, UserEducation

def clean_database():
    """Clean database, keep only rajeev.sharma@mail.ch."""
    db = SessionLocal()
    
    try:
        # Get all users except rajeev.sharma@mail.ch
        users_to_delete = db.query(User).filter(User.email != "rajeev.sharma@mail.ch").all()
        
        print(f"Found {len(users_to_delete)} users to delete:")
        for user in users_to_delete:
            print(f"  - {user.email} (ID: {user.id})")
        
        # Delete verification tokens for these users
        user_ids = [user.id for user in users_to_delete]
        if user_ids:
            db.query(VerificationToken).filter(VerificationToken.user_id.in_(user_ids)).delete(synchronize_session=False)
        
        # Delete related data
        db.query(UserProfile).filter(UserProfile.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(UserDocument).filter(UserDocument.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(UserSkill).filter(UserSkill.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(UserExperience).filter(UserExperience.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(UserEducation).filter(UserEducation.user_id.in_(user_ids)).delete(synchronize_session=False)
        
        # Delete users
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        
        # Reset rajeev.sharma@mail.ch to unverified for testing
        rajeev_user = db.query(User).filter(User.email == "rajeev.sharma@mail.ch").first()
        if rajeev_user:
            rajeev_user.is_verified = False
            rajeev_user.password_hash = "$5$rounds=535000$w4qH8LbN3sXpFzR7$N6Nq.4VW8kM9jL2Yq1P3rS5t7v9x1z3B5d7f9h1j3l"  # Hash for "Naukri123"
            print(f"\nReset rajeev.sharma@mail.ch:")
            print(f"  - Set is_verified = False")
            print(f"  - Reset password to Naukri123")
        
        db.commit()
        print(f"\nSUCCESS: Database cleaned successfully!")
        print(f"SUCCESS: Only rajeev.sharma@mail.ch remains (unverified)")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Error cleaning database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Cleaning database for fresh email verification test...")
    clean_database()