import pandas as pd
import sqlite3
from passlib.hash import bcrypt
import os

class UserDB:
    def __init__(self):
        self.db_path = "auth/users.db"
        self._init_db()
        
    def _init_db(self):
        """Initialize the user database"""
        os.makedirs("auth", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            employee_id TEXT,
            is_admin BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE
        )
        """)
        
        # Create admin if not exists
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            self._create_user(
                username="admin",
                password="admin123",  # Change this in production!
                is_admin=True
            )
        
        conn.commit()
        conn.close()
    
    def _create_user(self, username, password, employee_id=None, is_admin=False):
        """Create a new user"""
        hashed_password = bcrypt.hash(password)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO users (username, password, employee_id, is_admin)
        VALUES (?, ?, ?, ?)
        """, (username, hashed_password, employee_id, is_admin))
        
        conn.commit()
        conn.close()
        
    def verify_user(self, username, password):
        """Verify user credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT password, is_admin, employee_id FROM users 
        WHERE username=? AND is_active=TRUE
        """, (username,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and bcrypt.verify(password, result[0]):
            return {
                "authenticated": True,
                "is_admin": result[1],
                "employee_id": result[2]
            }
        return {"authenticated": False}
    
    def create_employee_user(self, employee_id, username, password):
        """Create a user account for an employee"""
        self._create_user(
            username=username,
            password=password,
            employee_id=employee_id,
            is_admin=False
        )
    
    def user_exists(self, username):
        """Check if username exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        return bool(result)
    
    def get_all_users(self):
        """Get all users for admin view"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT id, username, employee_id, is_admin, is_active FROM users", conn)
        conn.close()
        return df