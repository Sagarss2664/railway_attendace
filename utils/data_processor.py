import pandas as pd
from datetime import datetime, time
import numpy as np

class DataProcessor:
    def __init__(self):
        self.employees = None
        self.shifts = None
        self.attendance = None
        self.merged_data = None
        
    def load_data(self, employee_path, shifts_path, attendance_path):
        """Load all Excel files into DataFrames"""
        self.employees = pd.read_excel(employee_path)
        self.shifts = pd.read_excel(shifts_path)
        self.attendance = pd.read_excel(attendance_path)
        
        # Clean data
        self._clean_data()
        
        # Merge data
        self._merge_data()
        
        # Calculate metrics
        self._calculate_metrics()
        
        return self.merged_data
    
    def _clean_data(self):
        """Clean and preprocess data"""
        # Convert timestamps
        self.attendance['Timestamp'] = pd.to_datetime(self.attendance['Timestamp'])
        
        # Extract date from timestamp for attendance
        self.attendance['Date'] = self.attendance['Timestamp'].dt.date
        
        # Convert shift times to datetime
        self.shifts['Shift_Date'] = pd.to_datetime(self.shifts['Shift_Date']).dt.date
        self.shifts['Shift_Start'] = pd.to_datetime(self.shifts['Shift_Start'], format='%H:%M').dt.time
        self.shifts['Shift_End'] = pd.to_datetime(self.shifts['Shift_End'], format='%H:%M').dt.time
        
        # Clean employee data
        self.employees['Employee_ID'] = self.employees['Employee_ID'].astype(str)
        
    def _merge_data(self):
        """Merge all data sources"""
        # Merge attendance with shifts
        merged = pd.merge(
            self.attendance,
            self.shifts,
            left_on=['Employee_ID', 'Shift_ID'],
            right_on=['Employee_ID', 'Shift_ID'],
            how='left'
        )
        
        # Merge with employee data
        self.merged_data = pd.merge(
            merged,
            self.employees,
            on='Employee_ID',
            how='left'
        )
        
    def _calculate_metrics(self):
        """Calculate attendance metrics"""
        # Calculate late arrivals
        def calculate_late_status(row):
            if row['Type'] == 'Check-in':
                shift_start = datetime.combine(row['Shift_Date'], row['Shift_Start'])
                check_in = row['Timestamp']
                if check_in > shift_start:
                    return 'Late'
                return 'On Time'
            return None
            
        self.merged_data['Late_Status'] = self.merged_data.apply(calculate_late_status, axis=1)
        
        # Calculate early departures
        def calculate_early_departure(row):
            if row['Type'] == 'Check-out':
                shift_end = datetime.combine(row['Shift_Date'], row['Shift_End'])
                check_out = row['Timestamp']
                if check_out < shift_end:
                    return 'Early'
                return 'On Time'
            return None
            
        self.merged_data['Early_Status'] = self.merged_data.apply(calculate_early_departure, axis=1)
        
        # Calculate shift duration
        check_ins = self.merged_data[self.merged_data['Type'] == 'Check-in']
        check_outs = self.merged_data[self.merged_data['Type'] == 'Check-out']
        
        durations = []
        for idx, row in check_ins.iterrows():
            employee_id = row['Employee_ID']
            shift_id = row['Shift_ID']
            check_in_time = row['Timestamp']
            
            # Find corresponding check-out
            check_out = check_outs[
                (check_outs['Employee_ID'] == employee_id) & 
                (check_outs['Shift_ID'] == shift_id)
            ]
            
            if not check_out.empty:
                check_out_time = check_out.iloc[0]['Timestamp']
                duration = (check_out_time - check_in_time).total_seconds() / 3600  # in hours
                durations.append(duration)
            else:
                durations.append(np.nan)
        
        # Add durations to check-ins
        check_ins['Duration_Hours'] = durations
        
        # Merge back
        self.merged_data = pd.merge(
            self.merged_data,
            check_ins[['Employee_ID', 'Shift_ID', 'Duration_Hours']],
            on=['Employee_ID', 'Shift_ID'],
            how='left'
        )
        
    def get_employee_attendance(self, employee_id):
        """Get attendance data for specific employee"""
        return self.merged_data[self.merged_data['Employee_ID'] == employee_id]
    
    def get_department_stats(self, department):
        """Get statistics for specific department"""
        dept_data = self.merged_data[self.merged_data['Department'] == department]
        return dept_data
    
    def get_location_stats(self, location):
        """Get statistics for specific location"""
        loc_data = self.merged_data[self.merged_data['Location'] == location]
        return loc_data