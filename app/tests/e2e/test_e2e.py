import pytest
import requests
import time
import json

class TestE2E:
    """End-to-end tests for the complete application flow"""
    
    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the application"""
        return "http://localhost:5000"
    
    @pytest.fixture(scope="class")
    def auth_token(self, base_url):
        """Get authentication token for E2E tests"""
        # Register a test user
        user_data = {
            'username': 'e2euser',
            'email': 'e2e@example.com',
            'password': 'e2epass123',
            'first_name': 'E2E',
            'last_name': 'User'
        }
        
        response = requests.post(f"{base_url}/api/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Login to get token
        login_data = {
            'username': 'e2euser',
            'password': 'e2epass123'
        }
        
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        assert response.status_code == 200
        
        return response.json()['access_token']
    
    def test_complete_patient_workflow(self, base_url, auth_token):
        """Test complete patient management workflow"""
        headers = {'Authorization': f'Bearer {auth_token}'}
        
        # 1. Create a patient
        patient_data = {
            'patient_id': 'PAT-E2E-001',
            'first_name': 'E2E',
            'last_name': 'Patient',
            'date_of_birth': '1985-03-15',
            'gender': 'Male',
            'phone': '+1234567890',
            'email': 'e2e.patient@example.com',
            'address': '123 E2E Street, Test City, TC 12345',
            'emergency_contact_name': 'Emergency Contact',
            'emergency_contact_phone': '+1234567891',
            'medical_history': 'No significant medical history',
            'allergies': 'None known',
            'current_medications': 'None',
            'insurance_provider': 'E2E Insurance',
            'insurance_number': 'E2E123456789',
            'status': 'active'
        }
        
        response = requests.post(f"{base_url}/api/patients/", json=patient_data, headers=headers)
        assert response.status_code == 201
        created_patient = response.json()['patient']
        patient_id = created_patient['id']
        
        # 2. Get the created patient
        response = requests.get(f"{base_url}/api/patients/{patient_id}", headers=headers)
        assert response.status_code == 200
        retrieved_patient = response.json()['patient']
        assert retrieved_patient['patient_id'] == 'PAT-E2E-001'
        assert retrieved_patient['first_name'] == 'E2E'
        
        # 3. Update the patient
        update_data = {
            'first_name': 'Updated E2E',
            'phone': '+1987654321',
            'medical_history': 'Updated medical history'
        }
        
        response = requests.put(f"{base_url}/api/patients/{patient_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        updated_patient = response.json()['patient']
        assert updated_patient['first_name'] == 'Updated E2E'
        assert updated_patient['phone'] == '+1987654321'
        assert updated_patient['medical_history'] == 'Updated medical history'
        
        # 4. Get all patients and verify the patient is in the list
        response = requests.get(f"{base_url}/api/patients/", headers=headers)
        assert response.status_code == 200
        patients_data = response.json()
        assert patients_data['total'] >= 1
        
        # Find our patient in the list
        our_patient = None
        for patient in patients_data['patients']:
            if patient['id'] == patient_id:
                our_patient = patient
                break
        
        assert our_patient is not None
        assert our_patient['first_name'] == 'Updated E2E'
        
        # 5. Search for the patient
        response = requests.get(f"{base_url}/api/patients/?search=E2E", headers=headers)
        assert response.status_code == 200
        search_results = response.json()
        assert search_results['total'] >= 1
        
        # 6. Soft delete the patient
        response = requests.delete(f"{base_url}/api/patients/{patient_id}", headers=headers)
        assert response.status_code == 200
        
        # 7. Verify patient is soft deleted (status = inactive)
        response = requests.get(f"{base_url}/api/patients/{patient_id}", headers=headers)
        assert response.status_code == 200
        deleted_patient = response.json()['patient']
        assert deleted_patient['status'] == 'inactive'
        
        # 8. Restore the patient
        response = requests.post(f"{base_url}/api/patients/{patient_id}/restore", headers=headers)
        assert response.status_code == 200
        restored_patient = response.json()['patient']
        assert restored_patient['status'] == 'active'
        
        # 9. Verify patient is restored
        response = requests.get(f"{base_url}/api/patients/{patient_id}", headers=headers)
        assert response.status_code == 200
        final_patient = response.json()['patient']
        assert final_patient['status'] == 'active'
    
    def test_user_profile_management(self, base_url, auth_token):
        """Test user profile management workflow"""
        headers = {'Authorization': f'Bearer {auth_token}'}
        
        # 1. Get current profile
        response = requests.get(f"{base_url}/api/auth/profile", headers=headers)
        assert response.status_code == 200
        profile = response.json()['user']
        original_first_name = profile['first_name']
        
        # 2. Update profile
        update_data = {
            'first_name': 'Updated E2E',
            'last_name': 'Updated User'
        }
        
        response = requests.put(f"{base_url}/api/auth/profile", json=update_data, headers=headers)
        assert response.status_code == 200
        updated_profile = response.json()['user']
        assert updated_profile['first_name'] == 'Updated E2E'
        assert updated_profile['last_name'] == 'Updated User'
        
        # 3. Change password
        password_data = {
            'current_password': 'e2epass123',
            'new_password': 'newe2epass123'
        }
        
        response = requests.post(f"{base_url}/api/auth/change-password", json=password_data, headers=headers)
        assert response.status_code == 200
        
        # 4. Login with new password
        login_data = {
            'username': 'e2euser',
            'password': 'newe2epass123'
        }
        
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        assert response.status_code == 200
        new_token = response.json()['access_token']
        assert new_token is not None
    
    def test_error_handling(self, base_url):
        """Test error handling scenarios"""
        # 1. Test unauthorized access
        response = requests.get(f"{base_url}/api/patients/")
        assert response.status_code == 401
        
        # 2. Test invalid login
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }
        
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        assert response.status_code == 401
        
        # 3. Test invalid registration data
        invalid_user_data = {
            'username': 'ab',  # Too short
            'email': 'invalid-email',
            'password': '123'  # Too weak
        }
        
        response = requests.post(f"{base_url}/api/auth/register", json=invalid_user_data)
        assert response.status_code == 400
        
        # 4. Test accessing non-existent patient
        # First get a valid token
        user_data = {
            'username': 'erroruser',
            'email': 'error@example.com',
            'password': 'errorpass123',
            'first_name': 'Error',
            'last_name': 'User'
        }
        
        requests.post(f"{base_url}/api/auth/register", json=user_data)
        
        login_data = {
            'username': 'erroruser',
            'password': 'errorpass123'
        }
        
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        token = response.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(f"{base_url}/api/patients/999", headers=headers)
        assert response.status_code == 404
    
    def test_health_check(self, base_url):
        """Test health check endpoint"""
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'patient-api'
