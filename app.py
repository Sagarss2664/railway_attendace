import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_processor import DataProcessor
from auth.authentication import Authentication
from st_aggrid import AgGrid, GridOptionsBuilder

# Initialize authentication
auth = Authentication()

# Page configuration
st.set_page_config(
    page_title="SWR Workforce Tracking",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    processor = DataProcessor()
    data = processor.load_data(
        employee_path="data/employee.xlsx",
        shifts_path="data/shifts.xlsx",
        attendance_path="data/attendance.xlsx"
    )
    return processor, data

# Initialize session state
if 'data_loaded' not in st.session_state:
    processor, data = load_data()
    st.session_state.processor = processor
    st.session_state.data = data
    st.session_state.data_loaded = True
else:
    processor = st.session_state.processor
    data = st.session_state.data

# Login/Logout in sidebar
if not auth.authenticated:
    st.sidebar.title("Login")
    auth.login_form()
else:
    st.sidebar.title(f"Welcome, {auth.current_user}")
    if st.sidebar.button("Logout"):
        auth.logout()

# Main app - only show if authenticated
if auth.authenticated:
    # Admin features
    if auth.is_admin:
        st.sidebar.title("Admin Panel")
        admin_option = st.sidebar.radio(
            "Admin Options",
            options=["Dashboard", "User Management"]
        )
        
        if admin_option == "User Management":
            st.title("User Management")
            
            # Create new user
            with st.expander("Create New User"):
                with st.form("new_user_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    employee_id = st.text_input("Employee ID (optional)")
                    is_admin = st.checkbox("Is Admin")
                    submit = st.form_submit_button("Create User")
                    
                    if submit:
                        if auth.user_db.user_exists(username):
                            st.error("Username already exists")
                        else:
                            auth.user_db._create_user(
                                username=username,
                                password=password,
                                employee_id=employee_id,
                                is_admin=is_admin
                            )
                            st.success(f"User {username} created successfully!")
            
            # View all users
            st.subheader("All Users")
            users = auth.user_db.get_all_users()
            st.dataframe(users)
    
    # Employee features
    if not auth.is_admin and auth.employee_id:
        st.sidebar.title("Employee Options")
        emp_option = st.sidebar.radio(
            "Employee View",
            options=["My Attendance", "My Profile"]
        )
        
        if emp_option == "My Attendance":
            st.title("My Attendance Records")
            emp_data = processor.get_employee_attendance(auth.employee_id)
            
            # Display attendance records
            gb = GridOptionsBuilder.from_dataframe(
                emp_data[['Shift_ID', 'Shift_Date', 'Shift_Start', 'Shift_End', 
                         'Timestamp', 'Type', 'Late_Status', 'Early_Status', 'Duration_Hours']]
            )
            gb.configure_pagination(paginationAutoPageSize=True)
            grid_options = gb.build()
            
            AgGrid(
                emp_data[['Shift_ID', 'Shift_Date', 'Shift_Start', 'Shift_End', 
                         'Timestamp', 'Type', 'Late_Status', 'Early_Status', 'Duration_Hours']],
                gridOptions=grid_options,
                height=400,
                width='100%'
            )
            
            # Attendance summary
            st.subheader("Attendance Summary")
            col1, col2, col3 = st.columns(3)
            total_shifts = len(emp_data['Shift_ID'].unique())
            late_shifts = (emp_data[emp_data['Type'] == 'Check-in']['Late_Status'] == 'Late').sum()
            early_departures = (emp_data[emp_data['Type'] == 'Check-out']['Early_Status'] == 'Early').sum()
            
            col1.metric("Total Shifts", total_shifts)
            col2.metric("Late Arrivals", late_shifts)
            col3.metric("Early Departures", early_departures)
        
        elif emp_option == "My Profile":
            st.title("My Profile")
            employee_info = data[data['Employee_ID'] == auth.employee_id][
                ['Employee_ID', 'full_name', 'Department', 'Designation', 'Base_Location']
            ].iloc[0]
            
            st.write(f"**Employee ID:** {employee_info['Employee_ID']}")
            st.write(f"**Name:** {employee_info['full_name']}")
            st.write(f"**Department:** {employee_info['Department']}")
            st.write(f"**Designation:** {employee_info['Designation']}")
            st.write(f"**Base Location:** {employee_info['Base_Location']}")
    
    # Main dashboard (for admin)
    if auth.is_admin:
        # Sidebar filters
        st.sidebar.title("Filters")
        view_option = st.sidebar.radio(
            "View By",
            options=["Overview", "Department", "Location", "Employee"]
        )
        
        # Overview Dashboard
        if view_option == "Overview":
            st.subheader("Overall Statistics")
            
            # KPI Metrics
            col1, col2, col3, col4 = st.columns(4)
            total_employees = len(data['Employee_ID'].unique())
            total_shifts = len(data['Shift_ID'].unique())
            avg_duration = data['Duration_Hours'].mean()
            late_percentage = (data['Late_Status'] == 'Late').mean() * 100
            
            col1.metric("Total Employees", total_employees)
            col2.metric("Total Shifts Tracked", total_shifts)
            col3.metric("Avg Shift Duration (hrs)", f"{avg_duration:.2f}")
            col4.metric("Late Arrivals (%)", f"{late_percentage:.1f}%")
            
            # Department Distribution
            st.subheader("Department Distribution")
            dept_counts = data['Department'].value_counts().reset_index()
            dept_counts.columns = ['Department', 'Count']
            
            fig1 = px.pie(
                dept_counts, 
                values='Count', 
                names='Department',
                title='Shift Distribution by Department'
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Location Analysis
            st.subheader("Location Analysis")
            loc_counts = data['Location'].value_counts().reset_index()
            loc_counts.columns = ['Location', 'Count']
            
            fig2 = px.bar(
                loc_counts,
                x='Location',
                y='Count',
                color='Location',
                title='Shift Distribution by Location'
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Department View
        elif view_option == "Department":
            st.subheader("Department Analysis")
            
            departments = data['Department'].unique()
            selected_dept = st.selectbox("Select Department", departments)
            
            dept_data = processor.get_department_stats(selected_dept)
            
            # Department KPIs
            col1, col2, col3 = st.columns(3)
            dept_employees = len(dept_data['Employee_ID'].unique())
            dept_shifts = len(dept_data['Shift_ID'].unique())
            dept_late = (dept_data['Late_Status'] == 'Late').mean() * 100
            
            col1.metric("Employees in Department", dept_employees)
            col2.metric("Shifts in Department", dept_shifts)
            col3.metric("Late Arrivals (%)", f"{dept_late:.1f}%")
            
            # Employee List
            st.subheader(f"Employees in {selected_dept}")
            employees = dept_data[['Employee_ID', 'full_name', 'Designation']].drop_duplicates()
            st.dataframe(employees)
        
        # Location View
        elif view_option == "Location":
            st.subheader("Location Analysis")
            
            locations = data['Location'].unique()
            selected_loc = st.selectbox("Select Location", locations)
            
            loc_data = processor.get_location_stats(selected_loc)
            
            # Location KPIs
            col1, col2, col3 = st.columns(3)
            loc_employees = len(loc_data['Employee_ID'].unique())
            loc_shifts = len(loc_data['Shift_ID'].unique())
            loc_late = (loc_data['Late_Status'] == 'Late').mean() * 100
            
            col1.metric("Employees at Location", loc_employees)
            col2.metric("Shifts at Location", loc_shifts)
            col3.metric("Late Arrivals (%)", f"{loc_late:.1f}%")
        
        # Employee View
        elif view_option == "Employee":
            st.subheader("Employee Analysis")
            
            employees = data[['Employee_ID', 'full_name', 'Department']].drop_duplicates()
            employee_list = [f"{row['Employee_ID']} - {row['full_name']} ({row['Department']})" 
                            for _, row in employees.iterrows()]
            
            selected_employee = st.selectbox("Select Employee", employee_list)
            employee_id = selected_employee.split(" - ")[0]
            
            emp_data = processor.get_employee_attendance(employee_id)
            employee_info = emp_data[['Employee_ID', 'full_name', 'Department', 'Designation', 'Base_Location']].iloc[0]
            
            # Employee Info
            st.subheader("Employee Information")
            col1, col2, col3 = st.columns(3)
            col1.metric("Employee ID", employee_info['Employee_ID'])
            col2.metric("Name", employee_info['full_name'])
            col3.metric("Department", employee_info['Department'])
            
            # Attendance Records
            st.subheader("Attendance Records")
            AgGrid(
                emp_data[['Shift_ID', 'Shift_Date', 'Shift_Start', 'Shift_End', 
                         'Timestamp', 'Type', 'Late_Status', 'Early_Status', 'Duration_Hours']]
            )
    
    # Data Export
    if auth.is_admin:
        st.sidebar.markdown("---")
        if st.sidebar.button("Export Current View Data"):
            if view_option == "Overview":
                export_data = data
            elif view_option == "Department":
                export_data = processor.get_department_stats(selected_dept)
            elif view_option == "Location":
                export_data = processor.get_location_stats(selected_loc)
            elif view_option == "Employee":
                export_data = processor.get_employee_attendance(employee_id)
            
            st.sidebar.download_button(
                label="Download as CSV",
                data=export_data.to_csv(index=False).encode('utf-8'),
                file_name=f"swr_data_{view_option.lower()}.csv",
                mime='text/csv'
            )

# About section
st.sidebar.markdown("---")
st.sidebar.info("""
**South Western Railway**  
Workforce Tracking System  
Version 2.0 (with Authentication)  
[GitHub Repository](#)
""")