from app.models.database import SessionLocal, UserProfile

def populate_test_user():
    db = SessionLocal()
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == 1).first()
        if profile:
            profile.dob = "16.12.1976"
            profile.nationality = "India"
            profile.marital_status = "married"
            profile.work_auth = "C"
            db.commit()
            print("Profile updated for User 1.")
        else:
            print("Profile not found for User 1.")
    finally:
        db.close()

if __name__ == "__main__":
    populate_test_user()
