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
        assert 'Role must be one of: user, admin, doctor' in errors
    
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
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-15',
            'gender': 'Male',
            'phone': '+1234567890',
            'email': 'john.doe@example.com'
        }
        
        errors = validate_patient_data(patient_data)
        assert len(errors) == 0
    
    def test_validate_patient_data_missing_required_fields(self):
        """Test patient data validation with missing required fields"""
        patient_data = {
            'first_name': 'John'
        }
        
        errors = validate_patient_data(patient_data)
        assert 'last_name is required' in errors
        assert 'date_of_birth is required' in errors
        assert 'gender is required' in errors
    
    def test_validate_patient_data_invalid_date(self):
        """Test patient data validation with invalid date"""
        patient_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': 'invalid-date',
            'gender': 'Male'
        }
        
        errors = validate_patient_data(patient_data)
        assert 'Invalid date format. Use YYYY-MM-DD' in errors
    
    def test_validate_patient_data_future_date(self):
        """Test patient data validation with future date"""
        patient_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '2030-01-15',
            'gender': 'Male'
        }
        
        errors = validate_patient_data(patient_data)
        assert 'Date of birth cannot be in the future' in errors
    
    def test_validate_patient_data_invalid_gender(self):
        """Test patient data validation with invalid gender"""
        patient_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-15',
            'gender': 'Invalid'
        }
        
        errors = validate_patient_data(patient_data)
        assert 'Gender must be one of: Male, Female, Other' in errors
    
    def test_validate_patient_data_invalid_email(self):
        """Test patient data validation with invalid email"""
        patient_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-15',
            'gender': 'Male',
            'email': 'invalid-email'
        }
        
        errors = validate_patient_data(patient_data)
        assert 'Invalid email format' in errors
    
    def test_validate_patient_data_invalid_phone(self):
        """Test patient data validation with invalid phone"""
        patient_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-15',
            'gender': 'Male',
            'phone': '123'  # Too short
        }
        
        errors = validate_patient_data(patient_data)
        assert 'Invalid phone number format' in errors
    
    def test_validate_patient_data_invalid_status(self):
        """Test patient data validation with invalid status"""
        patient_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-15',
            'gender': 'Male',
            'status': 'invalid_status'
        }
        
        errors = validate_patient_data(patient_data)
        assert 'Status must be one of: active, inactive, discharged' in errors
