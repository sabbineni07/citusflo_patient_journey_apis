import pytest
from app.utils.validators import validate_user_data, validate_login_data, validate_patient_data

class TestValidators:
    """Test cases for validation functions"""
    
    def test_validate_user_data_valid(self):
        """Test valid user data validation"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        errors = validate_user_data(user_data)
        assert len(errors) == 0
    
    def test_validate_user_data_missing_fields(self):
        """Test user data validation with missing fields"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        errors = validate_user_data(user_data)
        assert len(errors) > 0
        assert 'password is required' in errors
        assert 'first_name is required' in errors
        assert 'last_name is required' in errors
    
    def test_validate_user_data_invalid_username(self):
        """Test user data validation with invalid username"""
        user_data = {
            'username': 'ab',  # Too short
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        errors = validate_user_data(user_data)
        assert 'Username must be at least 3 characters long' in errors
    
    def test_validate_user_data_invalid_username_characters(self):
        """Test user data validation with invalid username characters"""
        user_data = {
            'username': 'test@user!',  # Invalid characters
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        errors = validate_user_data(user_data)
        assert 'Username can only contain letters, numbers, and underscores' in errors
    
    def test_validate_user_data_invalid_email(self):
        """Test user data validation with invalid email"""
        user_data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        errors = validate_user_data(user_data)
        assert 'Invalid email format' in errors
    
    def test_validate_user_data_weak_password(self):
        """Test user data validation with weak password"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123',  # Too short and no letters
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        errors = validate_user_data(user_data)
        assert 'Password must be at least 6 characters long' in errors
        assert 'Password must contain at least one letter' in errors
    
    def test_validate_user_data_password_no_numbers(self):
        """Test user data validation with password containing no numbers"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass',  # No numbers
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        errors = validate_user_data(user_data)
        assert 'Password must contain at least one number' in errors
    
    def test_validate_user_data_invalid_role(self):
        """Test user data validation with invalid role"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'invalid_role'
        }
        
        errors = validate_user_data(user_data)
        assert 'Role must be one of: user, admin, doctor, nurse' in errors
    
    def test_validate_login_data_valid(self):
        """Test valid login data validation"""
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        errors = validate_login_data(login_data)
        assert len(errors) == 0
    
    def test_validate_login_data_missing_fields(self):
        """Test login data validation with missing fields"""
        login_data = {
            'username': 'testuser'
        }
        
        errors = validate_login_data(login_data)
        assert 'Password is required' in errors
    
    def test_validate_patient_data_valid(self):
        """Test valid patient data validation"""
        patient_data = {
            'caseManagerName': 'John Smith',
            'phoneNumber': '+1234567890',
            'facilityName': 'General Hospital',
            'patientName': 'Jane Doe',
            'date': '2024-01-15',
            'referralReceived': True,
            'insuranceVerification': False,
            'facility_id': '5'
        }

        errors = validate_patient_data(patient_data)
        assert len(errors) == 0

    def test_validate_patient_data_missing_required_fields(self):
        """Test patient data validation with missing required fields"""
        patient_data = {}

        errors = validate_patient_data(patient_data)
        assert 'caseManagerName is required' in errors
        assert 'phoneNumber is required' in errors
        assert 'facilityName is required' in errors
        assert 'patientName is required' in errors
        assert 'date is required' in errors

    def test_validate_patient_data_invalid_date(self):
        """Test patient data validation with invalid date"""
        patient_data = {
            'caseManagerName': 'John Smith',
            'phoneNumber': '+1234567890',
            'facilityName': 'General Hospital',
            'patientName': 'Jane Doe',
            'date': 'invalid-date'
        }

        errors = validate_patient_data(patient_data)
        assert 'Invalid date format. Use YYYY-MM-DD' in errors

    def test_validate_patient_data_future_date(self):
        """Test patient data validation with future date"""
        patient_data = {
            'caseManagerName': 'John Smith',
            'phoneNumber': '+1234567890',
            'facilityName': 'General Hospital',
            'patientName': 'Jane Doe',
            'date': '2999-01-15'
        }

        errors = validate_patient_data(patient_data)
        assert 'Date cannot be in the future' in errors

    def test_validate_patient_data_invalid_phone(self):
        """Test patient data validation with invalid phone number"""
        patient_data = {
            'caseManagerName': 'John Smith',
            'phoneNumber': '123',
            'facilityName': 'General Hospital',
            'patientName': 'Jane Doe',
            'date': '2024-01-15'
        }

        errors = validate_patient_data(patient_data)
        assert 'Invalid phone number format' in errors

    def test_validate_patient_data_invalid_boolean(self):
        """Test patient data validation with invalid boolean value"""
        patient_data = {
            'caseManagerName': 'John Smith',
            'phoneNumber': '+1234567890',
            'facilityName': 'General Hospital',
            'patientName': 'Jane Doe',
            'date': '2024-01-15',
            'referralReceived': 'yes'
        }

        errors = validate_patient_data(patient_data)
        assert 'referralReceived must be a boolean value' in errors

    def test_validate_patient_data_invalid_facility_id(self):
        """Test patient data validation with invalid facility id"""
        patient_data = {
            'caseManagerName': 'John Smith',
            'phoneNumber': '+1234567890',
            'facilityName': 'General Hospital',
            'patientName': 'Jane Doe',
            'date': '2024-01-15',
            'facility_id': 'abc'
        }

        errors = validate_patient_data(patient_data)
        assert 'Facility ID must be a valid integer' in errors
