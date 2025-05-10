import streamlit as st
from auth.user_db import UserDB

class Authentication:
    def __init__(self):
        self.user_db = UserDB()
        self.authenticated = False
        self.current_user = None
        self.is_admin = False
        self.employee_id = None
        
    def login_form(self):
        """Render login form and handle authentication"""
        with st.form("Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                result = self.user_db.verify_user(username, password)
                if result["authenticated"]:
                    self.authenticated = True
                    self.current_user = username
                    self.is_admin = result["is_admin"]
                    self.employee_id = result["employee_id"]
                    st.success("Login successful!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")
        
        return self.authenticated
    
    def logout(self):
        """Logout the current user"""
        self.authenticated = False
        self.current_user = None
        self.is_admin = False
        self.employee_id = None
        st.experimental_rerun()
    
    def admin_required(self):
        """Check if user is admin, show error if not"""
        if not self.is_admin:
            st.error("Admin privileges required to access this page")
            return False
        return True
    
    def protect_route(self):
        """Protect a route by checking authentication"""
        if not self.authenticated:
            st.warning("Please login to access this page")
            return False
        return True