import pytest
import json

class TestPatientRoutes:
    """Integration tests for patient routes"""
    
    def test_create_patient_success(self, client, auth_headers, sample_patient_data):
        """Test successful patient creation"""
        response = client.post('/api/patients/', json=sample_patient_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Patient created successfully'
        assert data['patient']['patient_id'] == 'PAT-2024-001'
        assert data['patient']['first_name'] == 'John'
        assert data['patient']['last_name'] == 'Doe'
    
    def test_create_patient_duplicate_id(self, client, auth_headers, sample_patient_data):
        """Test creating patient with duplicate patient_id"""
        # Create first patient
        client.post('/api/patients/', json=sample_patient_data, headers=auth_headers)
        
        # Try to create second patient with same patient_id
        response = client.post('/api/patients/', json=sample_patient_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Patient ID already exists' in data['error']
    
    def test_create_patient_invalid_data(self, client, auth_headers):
        """Test creating patient with invalid data"""
        invalid_data = {
            'first_name': 'J',  # Too short
            'date_of_birth': 'invalid-date',
            'gender': 'Invalid'
        }
        
        response = client.post('/api/patients/', json=invalid_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'errors' in data
        assert len(data['errors']) > 0
    
    def test_create_patient_no_auth(self, client, sample_patient_data):
        """Test creating patient without authentication"""
        response = client.post('/api/patients/', json=sample_patient_data)
        
        assert response.status_code == 401
    
    def test_get_patients_success(self, client, auth_headers, sample_patient_data):
        """Test getting patients list"""
        # Create a patient first
        client.post('/api/patients/', json=sample_patient_data, headers=auth_headers)
        
        response = client.get('/api/patients/', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'patients' in data
        assert 'total' in data
        assert 'page' in data
        assert 'per_page' in data
        assert len(data['patients']) == 1
        assert data['total'] == 1
    
    def test_get_patients_with_pagination(self, client, auth_headers):
        """Test getting patients with pagination"""
        # Create multiple patients
        for i in range(15):
            patient_data = {
                'patient_id': f'PAT-2024-{i:03d}',
                'first_name': f'Patient{i}',
                'last_name': 'Test',
                'date_of_birth': '1990-01-15',
                'gender': 'Male',
                'status': 'active'
            }
            client.post('/api/patients/', json=patient_data, headers=auth_headers)
        
        # Test first page
        response = client.get('/api/patients/?page=1&per_page=10', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['patients']) == 10
        assert data['total'] == 15
        assert data['page'] == 1
        assert data['per_page'] == 10
        
        # Test second page
        response = client.get('/api/patients/?page=2&per_page=10', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['patients']) == 5
        assert data['page'] == 2
    
    def test_get_patients_with_search(self, client, auth_headers):
        """Test getting patients with search filter"""
        # Create patients with different names
        patient1_data = {
            'patient_id': 'PAT-2024-001',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-15',
            'gender': 'Male',
            'status': 'active'
        }
        
        patient2_data = {
            'patient_id': 'PAT-2024-002',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1985-05-20',
            'gender': 'Female',
            'status': 'active'
        }
        
        client.post('/api/patients/', json=patient1_data, headers=auth_headers)
        client.post('/api/patients/', json=patient2_data, headers=auth_headers)
        
        # Search by first name
        response = client.get('/api/patients/?search=John', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['patients']) == 1
        assert data['patients'][0]['first_name'] == 'John'
    
    def test_get_patients_with_status_filter(self, client, auth_headers):
        """Test getting patients with status filter"""
        # Create patients with different statuses
        patient1_data = {
            'patient_id': 'PAT-2024-001',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-15',
            'gender': 'Male',
            'status': 'active'
        }
        
        patient2_data = {
            'patient_id': 'PAT-2024-002',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1985-05-20',
            'gender': 'Female',
            'status': 'inactive'
        }
        
        client.post('/api/patients/', json=patient1_data, headers=auth_headers)
        client.post('/api/patients/', json=patient2_data, headers=auth_headers)
        
        # Filter by active status
        response = client.get('/api/patients/?status=active', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['patients']) == 1
        assert data['patients'][0]['status'] == 'active'
    
    def test_get_patient_by_id_success(self, client, auth_headers, sample_patient_data):
        """Test getting patient by ID"""
        # Create a patient first
        create_response = client.post('/api/patients/', json=sample_patient_data, headers=auth_headers)
        patient_id = create_response.get_json()['patient']['id']
        
        response = client.get(f'/api/patients/{patient_id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'patient' in data
        assert data['patient']['id'] == patient_id
        assert data['patient']['patient_id'] == 'PAT-2024-001'
    
    def test_get_patient_by_id_not_found(self, client, auth_headers):
        """Test getting non-existent patient by ID"""
        response = client.get('/api/patients/999', headers=auth_headers)
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'Patient not found' in data['error']
    
    def test_update_patient_success(self, client, auth_headers, sample_patient_data):
        """Test updating patient successfully"""
        # Create a patient first
        create_response = client.post('/api/patients/', json=sample_patient_data, headers=auth_headers)
        patient_id = create_response.get_json()['patient']['id']
        
        # Update patient
        update_data = {
            'first_name': 'Johnny',
            'phone': '+1234567890',
            'email': 'johnny.doe@example.com'
        }
        
        response = client.put(f'/api/patients/{patient_id}', json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Patient updated successfully'
        assert data['patient']['first_name'] == 'Johnny'
        assert data['patient']['phone'] == '+1234567890'
        assert data['patient']['email'] == 'johnny.doe@example.com'
    
    def test_update_patient_duplicate_id(self, client, auth_headers):
        """Test updating patient with duplicate patient_id"""
        # Create two patients
        patient1_data = {
            'patient_id': 'PAT-2024-001',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-15',
            'gender': 'Male',
            'status': 'active'
        }
        
        patient2_data = {
            'patient_id': 'PAT-2024-002',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1985-05-20',
            'gender': 'Female',
            'status': 'active'
        }
        
        create_response1 = client.post('/api/patients/', json=patient1_data, headers=auth_headers)
        create_response2 = client.post('/api/patients/', json=patient2_data, headers=auth_headers)
        
        patient1_id = create_response1.get_json()['patient']['id']
        
        # Try to update patient1 with patient2's ID
        update_data = {
            'patient_id': 'PAT-2024-002'
        }
        
        response = client.put(f'/api/patients/{patient1_id}', json=update_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Patient ID already exists' in data['error']
    
    def test_delete_patient_success(self, client, auth_headers, sample_patient_data):
        """Test deleting patient successfully"""
        # Create a patient first
        create_response = client.post('/api/patients/', json=sample_patient_data, headers=auth_headers)
        patient_id = create_response.get_json()['patient']['id']
        
        response = client.delete(f'/api/patients/{patient_id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Patient deleted successfully'
        
        # Verify patient is soft deleted
        get_response = client.get(f'/api/patients/{patient_id}', headers=auth_headers)
        assert get_response.status_code == 200
        patient_data = get_response.get_json()['patient']
        assert patient_data['status'] == 'inactive'
    
    def test_restore_patient_success(self, client, auth_headers, sample_patient_data):
        """Test restoring patient successfully"""
        # Create a patient first
        create_response = client.post('/api/patients/', json=sample_patient_data, headers=auth_headers)
        patient_id = create_response.get_json()['patient']['id']
        
        # Delete patient
        client.delete(f'/api/patients/{patient_id}', headers=auth_headers)
        
        # Restore patient
        response = client.post(f'/api/patients/{patient_id}/restore', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Patient restored successfully'
        assert data['patient']['status'] == 'active'
