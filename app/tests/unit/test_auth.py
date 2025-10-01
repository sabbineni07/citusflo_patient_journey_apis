import pytest
from app.models.user import User
from app.services.auth_service import AuthService

class TestAuthService:
    """Test cases for AuthService"""
    
    def test_create_user(self, app):
        """Test user creation"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            user = auth_service.create_user(user_data)
            
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.first_name == 'Test'
            assert user.last_name == 'User'
            assert user.check_password('testpass123')
            assert user.role == 'user'
            assert user.is_active == True
    
    def test_authenticate_user_success(self, app):
        """Test successful user authentication"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            auth_service.create_user(user_data)
            user = auth_service.authenticate_user('testuser', 'testpass123')
            
            assert user is not None
            assert user.username == 'testuser'
    
    def test_authenticate_user_failure(self, app):
        """Test failed user authentication"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            auth_service.create_user(user_data)
            user = auth_service.authenticate_user('testuser', 'wrongpassword')
            
            assert user is None
    
    def test_get_user_by_id(self, app):
        """Test getting user by ID"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            created_user = auth_service.create_user(user_data)
            user = auth_service.get_user_by_id(created_user.id)
            
            assert user is not None
            assert user.id == created_user.id
            assert user.username == 'testuser'
    
    def test_get_user_by_username(self, app):
        """Test getting user by username"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            auth_service.create_user(user_data)
            user = auth_service.get_user_by_username('testuser')
            
            assert user is not None
            assert user.username == 'testuser'
    
    def test_get_user_by_email(self, app):
        """Test getting user by email"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            auth_service.create_user(user_data)
            user = auth_service.get_user_by_email('test@example.com')
            
            assert user is not None
            assert user.email == 'test@example.com'
    
    def test_update_user(self, app):
        """Test updating user information"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            user = auth_service.create_user(user_data)
            update_data = {
                'first_name': 'Updated',
                'last_name': 'Name'
            }
            
            updated_user = auth_service.update_user(user, update_data)
            
            assert updated_user.first_name == 'Updated'
            assert updated_user.last_name == 'Name'
            assert updated_user.username == 'testuser'  # Should remain unchanged
    
    def test_deactivate_user(self, app):
        """Test deactivating user account"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            user = auth_service.create_user(user_data)
            assert user.is_active == True
            
            deactivated_user = auth_service.deactivate_user(user)
            assert deactivated_user.is_active == False
    
    def test_activate_user(self, app):
        """Test activating user account"""
        with app.app_context():
            auth_service = AuthService()
            user_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            user = auth_service.create_user(user_data)
            auth_service.deactivate_user(user)
            assert user.is_active == False
            
            activated_user = auth_service.activate_user(user)
            assert activated_user.is_active == True
