import pytest
import json

class TestAuthRoutes:
    """Integration tests for authentication routes"""
    
    def test_register_success(self, client):
        """Test successful user registration"""
        user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = client.post('/api/auth/register', json=user_data)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'User created successfully'
        assert data['user']['username'] == 'newuser'
        assert data['user']['email'] == 'newuser@example.com'
        assert 'password' not in data['user']
    
    def test_register_duplicate_username(self, client):
        """Test registration with duplicate username"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        # First registration
        client.post('/api/auth/register', json=user_data)
        
        # Second registration with same username
        user_data['email'] = 'different@example.com'
        response = client.post('/api/auth/register', json=user_data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Username already exists' in data['error']
    
    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        # First registration
        client.post('/api/auth/register', json=user_data)
        
        # Second registration with same email
        user_data['username'] = 'differentuser'
        response = client.post('/api/auth/register', json=user_data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Email already exists' in data['error']
    
    def test_register_invalid_data(self, client):
        """Test registration with invalid data"""
        user_data = {
            'username': 'ab',  # Too short
            'email': 'invalid-email',
            'password': '123',  # Too weak
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        response = client.post('/api/auth/register', json=user_data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'errors' in data
        assert len(data['errors']) > 0
    
    def test_login_success(self, client):
        """Test successful login"""
        # Register user first
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        client.post('/api/auth/register', json=user_data)
        
        # Login
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = client.post('/api/auth/login', json=login_data)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Login successful'
        assert 'access_token' in data
        assert data['user']['username'] == 'testuser'
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }
        
        response = client.post('/api/auth/login', json=login_data)
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'Invalid credentials' in data['error']
    
    def test_login_missing_data(self, client):
        """Test login with missing data"""
        login_data = {
            'username': 'testuser'
        }
        
        response = client.post('/api/auth/login', json=login_data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'errors' in data
    
    def test_get_profile_success(self, client, auth_headers):
        """Test getting user profile"""
        response = client.get('/api/auth/profile', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'user' in data
        assert data['user']['username'] == 'testuser'
    
    def test_get_profile_no_token(self, client):
        """Test getting profile without token"""
        response = client.get('/api/auth/profile')
        
        assert response.status_code == 401
    
    def test_update_profile_success(self, client, auth_headers):
        """Test updating user profile"""
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        
        response = client.put('/api/auth/profile', json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Profile updated successfully'
        assert data['user']['first_name'] == 'Updated'
        assert data['user']['last_name'] == 'Name'
    
    def test_update_profile_duplicate_email(self, client, auth_headers):
        """Test updating profile with duplicate email"""
        # Create another user
        user_data = {
            'username': 'otheruser',
            'email': 'other@example.com',
            'password': 'otherpass123',
            'first_name': 'Other',
            'last_name': 'User'
        }
        client.post('/api/auth/register', json=user_data)
        
        # Try to update profile with existing email
        update_data = {
            'email': 'other@example.com'
        }
        
        response = client.put('/api/auth/profile', json=update_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Email already exists' in data['error']
    
    def test_change_password_success(self, client, auth_headers):
        """Test changing password successfully"""
        password_data = {
            'current_password': 'testpass123',
            'new_password': 'newpass123'
        }
        
        response = client.post('/api/auth/change-password', json=password_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Password changed successfully'
    
    def test_change_password_wrong_current(self, client, auth_headers):
        """Test changing password with wrong current password"""
        password_data = {
            'current_password': 'wrongpassword',
            'new_password': 'newpass123'
        }
        
        response = client.post('/api/auth/change-password', json=password_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Current password is incorrect' in data['error']
    
    def test_change_password_missing_data(self, client, auth_headers):
        """Test changing password with missing data"""
        password_data = {
            'current_password': 'testpass123'
        }
        
        response = client.post('/api/auth/change-password', json=password_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Current password and new password are required' in data['error']
