#!/usr/bin/env python3
"""
Simple password reset using the same hashing as the auth service.
"""

import sqlite3
from passlib.hash import sha256_crypt

def reset_password():
    """Reset Rajeev's password to SecurePass123 using sha256_crypt."""
    try:
        conn = sqlite3.connect('career_revolution.db')
        cursor = conn.cursor()
        
        # Get Rajeev's user ID
        cursor.execute("SELECT id, email FROM users WHERE email='rajeev.sharma@mail.ch';")
        user = cursor.fetchone()
        
        if not user:
            print("User not found")
            return
        
        user_id, email = user
        print(f"Resetting password for: {email} (ID: {user_id})")
        
        # Hash the new password using sha256_crypt (same as auth service fallback)
        new_password = "SecurePass123"
        hashed_password = sha256_crypt.hash(new_password, rounds=30000)
        
        # Update password in database
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
        conn.commit()
        
        print(f"Password reset successful!")
        print(f"New password: {new_password}")
        
        # Verify the hash
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        stored_hash = cursor.fetchone()[0]
        
        if sha256_crypt.verify(new_password, stored_hash):
            print("Password verification: SUCCESS")
        else:
            print("Password verification: FAILED")
        
        conn.close()
        
        print("\nLogin credentials:")
        print(f"Email: {email}")
        print(f"Password: {new_password}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_password()