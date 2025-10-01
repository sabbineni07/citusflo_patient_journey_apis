import re
from datetime import datetime

def validate_user_data(data):
    """Validate user registration data"""
    errors = []
    
    # Required fields
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            errors.append(f'{field} is required')
    
    # Username validation
    if data.get('username'):
        username = data['username']
        if len(username) < 3:
            errors.append('Username must be at least 3 characters long')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('Username can only contain letters, numbers, and underscores')
    
    # Email validation
    if data.get('email'):
        email = data['email']
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            errors.append('Invalid email format')
    
    # Password validation
    if data.get('password'):
        password = data['password']
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long')
        if not re.search(r'[A-Za-z]', password):
            errors.append('Password must contain at least one letter')
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one number')
    
    # Name validation
    if data.get('first_name') and len(data['first_name']) < 2:
        errors.append('First name must be at least 2 characters long')
    
    if data.get('last_name') and len(data['last_name']) < 2:
        errors.append('Last name must be at least 2 characters long')
    
    # Role validation
    if data.get('role') and data['role'] not in ['user', 'admin', 'doctor', 'nurse']:
        errors.append('Role must be one of: user, admin, doctor, nurse')
    
    # Facility ID validation
    if data.get('facility_id'):
        facility_id = data['facility_id']
        if facility_id and str(facility_id).strip():
            try:
                int(facility_id)  # Validate it can be converted to integer
            except (ValueError, TypeError):
                errors.append('Facility ID must be a valid integer')
    
    return errors

def validate_login_data(data):
    """Validate user login data"""
    errors = []
    
    # Required fields
    if not data.get('username'):
        errors.append('Username is required')
    
    if not data.get('password'):
        errors.append('Password is required')
    
    return errors

def validate_patient_data(data, is_update=False):
    """Validate patient data"""
    errors = []
    
    # Required fields for creation
    if not is_update:
        required_fields = ['caseManagerName', 'phoneNumber', 'facilityName', 'patientName', 'date']
        for field in required_fields:
            if not data.get(field):
                errors.append(f'{field} is required')
    
    # Name validation
    if data.get('caseManagerName') and len(data['caseManagerName']) < 2:
        errors.append('Case manager name must be at least 2 characters long')
    
    if data.get('patientName') and len(data['patientName']) < 2:
        errors.append('Patient name must be at least 2 characters long')
    
    if data.get('facilityName') and len(data['facilityName']) < 2:
        errors.append('Facility name must be at least 2 characters long')
    
    # Date validation
    if data.get('date'):
        try:
            date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
            if date_obj > datetime.now().date():
                errors.append('Date cannot be in the future')
            if date_obj.year < 1900:
                errors.append('Date cannot be before 1900')
        except ValueError:
            errors.append('Invalid date format. Use YYYY-MM-DD')
    
    # Phone validation
    if data.get('phoneNumber'):
        phone = data['phoneNumber']
        phone_pattern = r'^\+?[\d\s\-\(\)]+$'
        if not re.match(phone_pattern, phone) or len(phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')) < 10:
            errors.append('Invalid phone number format')
    
    # Boolean field validation
    boolean_fields = ['referralReceived', 'insuranceVerification', 'familyAndPatientAware', 
                     'inPersonVisit', 'dischargedFromFacility', 'admitted', 'careFollowUp']
    for field in boolean_fields:
        if data.get(field) is not None and not isinstance(data[field], bool):
            errors.append(f'{field} must be a boolean value')
    
    # Facility ID validation
    if data.get('facility_id'):
        facility_id = data['facility_id']
        if facility_id and str(facility_id).strip():
            try:
                int(facility_id)  # Validate it can be converted to integer
            except (ValueError, TypeError):
                errors.append('Facility ID must be a valid integer')
    
    return errors
