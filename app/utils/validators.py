import re
from datetime import datetime
from app.models.role import Role

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
    
    # Password validation (HIPAA compliant - strong password requirements)
    if data.get('password'):
        password = data['password']
        if len(password) < 12:
            errors.append('Password must be at least 12 characters long')
        if not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter')
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter')
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\'\\:"|,.<>\/?]', password):
            errors.append('Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)')
    
    # Name validation
    if data.get('first_name') and len(data['first_name']) < 2:
        errors.append('First name must be at least 2 characters long')
    
    if data.get('last_name') and len(data['last_name']) < 2:
        errors.append('Last name must be at least 2 characters long')
    
    # Role validation - use role_id or role name
    # Wrap in try-except to handle database connection issues gracefully
    try:
        if data.get('role_id'):
            # Validate role_id exists
            try:
                role_id = int(data['role_id'])
                role = Role.query.get(role_id)
                if not role:
                    errors.append(f'Role ID {role_id} does not exist')
            except (ValueError, TypeError):
                errors.append('Role ID must be a valid integer')
            except Exception:
                # If database query fails, skip role validation (roles might not be initialized yet)
                pass
        elif data.get('role'):
            # Validate role name exists in roles table
            role_name = data['role']
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                try:
                    valid_roles = [r.name for r in Role.query.all()]
                    errors.append(f'Role must be one of: {", ".join(valid_roles) if valid_roles else "super_admin, admin, clinician, case_manager"}')
                except Exception:
                    # If database query fails, use default list including super_admin
                    errors.append('Role must be one of: super_admin, admin, clinician, case_manager')
    except Exception:
        # If database query fails completely, skip role validation
        # This allows registration to proceed if database is temporarily unavailable
        pass
    
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
            date_str = data['date']
            # Handle ISO format dates (may include time)
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            if ' ' in date_str:
                date_str = date_str.split(' ')[0]
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            if date_obj > datetime.now().date():
                errors.append('Date cannot be in the future')
            if date_obj.year < 1900:
                errors.append('Date cannot be before 1900')
        except ValueError:
            errors.append('Invalid date format. Use YYYY-MM-DD')
    
    # Date of birth validation
    if data.get('dateOfBirth'):
        try:
            dob_str = data['dateOfBirth']
            # Handle ISO format dates (may include time)
            if 'T' in dob_str:
                dob_str = dob_str.split('T')[0]
            if ' ' in dob_str:
                dob_str = dob_str.split(' ')[0]
            dob_obj = datetime.strptime(dob_str, '%Y-%m-%d').date()
            # Date of birth cannot be in the future
            if dob_obj > datetime.now().date():
                errors.append('Date of birth cannot be in the future')
            # Date of birth should be reasonable (not before 1900, not too far in past)
            if dob_obj.year < 1900:
                errors.append('Date of birth cannot be before 1900')
            if dob_obj.year > datetime.now().year:
                errors.append('Date of birth cannot be in the future')
        except ValueError:
            errors.append('Invalid date of birth format. Use YYYY-MM-DD')
    
    # Phone validation
    if data.get('phoneNumber'):
        phone = data['phoneNumber']
        phone_pattern = r'^\+?[\d\s\-\(\)]+$'
        if not re.match(phone_pattern, phone) or len(phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')) < 10:
            errors.append('Invalid phone number format')
    
    # Boolean field validation
    boolean_fields = ['referralReceived', 'insuranceVerification', 'familyAndPatientAware', 
                     'inPersonVisit', 'dischargedFromFacility', 'admitted', 'careFollowUp', 'active']
    for field in boolean_fields:
        if data.get(field) is not None and not isinstance(data[field], bool):
            errors.append(f'{field} must be a boolean value')
    
    # DateTime validation for admittedDatetime
    if data.get('admittedDatetime'):
        try:
            # Try to parse ISO format datetime
            datetime.fromisoformat(data['admittedDatetime'].replace('Z', '+00:00'))
        except (ValueError, AttributeError, TypeError):
            errors.append('admittedDatetime must be a valid ISO format datetime string (e.g., YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ)')
    
    # Facility ID validation
    if data.get('facility_id'):
        facility_id = data['facility_id']
        if facility_id and str(facility_id).strip():
            try:
                int(facility_id)  # Validate it can be converted to integer
            except (ValueError, TypeError):
                errors.append('Facility ID must be a valid integer')
    
    # Hospital ID validation
    if data.get('hospital_id'):
        hospital_id = data['hospital_id']
        if hospital_id and str(hospital_id).strip():
            try:
                hospital_id_int = int(hospital_id)
                # Validate hospital exists
                from app.models.hospital import Hospital
                hospital = Hospital.query.get(hospital_id_int)
                if not hospital:
                    errors.append(f'Hospital ID {hospital_id_int} does not exist')
            except (ValueError, TypeError):
                errors.append('Hospital ID must be a valid integer')
    
    # Hospital Name validation (if provided, validate format)
    if data.get('hospitalName'):
        hospital_name = data.get('hospitalName')
        if hospital_name and len(hospital_name.strip()) < 2:
            errors.append('Hospital name must be at least 2 characters long')
    
    return errors
