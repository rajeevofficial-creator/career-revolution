import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, User, UserProfile, UserExperience, UserEducation, UserSkill

def populate_master_data():
    with open("master_cv_data.json", "r") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            print("User not found")
            return

        # 1. Update Profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if profile:
            profile.phone = data["personal_info"]["phone"]
            profile.location = data["personal_info"]["location"]
            profile.summary = data["personal_info"]["summary"]
            profile.linkedin_url = data["personal_info"]["linkedin_url"]
        
        # 2. Clear and Update Experience
        db.query(UserExperience).filter(UserExperience.user_id == user.id).delete()
        for exp in data["experience"]:
            start_date = datetime.strptime(exp["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(exp["end_date"], "%Y-%m-%d") if exp.get("end_date") else None
            
            new_exp = UserExperience(
                user_id=user.id,
                company=exp["company"],
                position=exp["title"],
                start_date=start_date,
                end_date=end_date,
                description=exp["description"],
                achievements=exp.get("achievements", "")
            )
            db.add(new_exp)

        # 3. Clear and Update Education
        db.query(UserEducation).filter(UserEducation.user_id == user.id).delete()
        for edu in data["education"]:
            start_date = datetime.strptime(edu["start_date"], "%Y-%m-%d") if edu.get("start_date") else None
            end_date = datetime.strptime(edu["end_date"], "%Y-%m-%d") if edu.get("end_date") else None
            
            new_edu = UserEducation(
                user_id=user.id,
                institution=edu["institution"],
                degree=edu["degree"],
                field_of_study=edu.get("field_of_study", ""),
                start_date=start_date,
                end_date=end_date
            )
            db.add(new_edu)

        # 4. Clear and Update Skills
        db.query(UserSkill).filter(UserSkill.user_id == user.id).delete()
        for skill_name in data["skills"]:
            new_skill = UserSkill(
                user_id=user.id,
                skill_name=skill_name,
                category="technical"
            )
            db.add(new_skill)
            
        for cert in data.get("certifications", []):
            new_cert = UserSkill(
                user_id=user.id,
                skill_name=cert,
                category="certification"
            )
            db.add(new_cert)

        db.commit()
        print("Master data populated successfully!")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_master_data()
