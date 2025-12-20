import pytest
from app.models.patient import Patient
from app import db
from datetime import datetime, date


@pytest.mark.integration
class TestNewPatientFields:
    """Integration tests for new patient fields (active, admitted_datetime, notes, date_of_birth)"""
    
    def test_create_patient_with_active_field(self, client, auth_headers):
        """Test creating patient with active field"""
        with client.application.app_context():
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'active': True
            }
            
            response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            assert response.status_code == 201
            
            patient_id = response.get_json()['patient']['id']
            patient = Patient.query.get(patient_id)
            
            assert patient.active == True
    
    def test_create_patient_with_admitted_datetime(self, client, auth_headers):
        """Test creating patient with admitted_datetime"""
        with client.application.app_context():
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'admitted': True,
                'admittedDatetime': '2024-01-15T10:30:00Z'
            }
            
            response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            assert response.status_code == 201
            
            patient_id = response.get_json()['patient']['id']
            patient = Patient.query.get(patient_id)
            
            assert patient.admitted == True
            assert patient.admitted_datetime is not None
            assert isinstance(patient.admitted_datetime, datetime)
    
    def test_create_patient_with_notes(self, client, auth_headers):
        """Test creating patient with notes field"""
        with client.application.app_context():
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'notes': 'This is a test note about the patient.'
            }
            
            response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            assert response.status_code == 201
            
            patient_id = response.get_json()['patient']['id']
            patient = Patient.query.get(patient_id)
            
            assert patient.notes == 'This is a test note about the patient.'
    
    def test_create_patient_with_date_of_birth(self, client, auth_headers):
        """Test creating patient with date_of_birth"""
        with client.application.app_context():
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'dateOfBirth': '1990-05-15'
            }
            
            response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            assert response.status_code == 201
            
            patient_id = response.get_json()['patient']['id']
            patient = Patient.query.get(patient_id)
            
            assert patient.date_of_birth is not None
            assert isinstance(patient.date_of_birth, date)
            assert patient.date_of_birth == date(1990, 5, 15)
    
    def test_update_patient_active_field(self, client, auth_headers):
        """Test updating patient active field"""
        with client.application.app_context():
            # Create patient
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'active': True
            }
            
            create_response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            patient_id = create_response.get_json()['patient']['id']
            
            # Update active field
            update_data = {'active': False}
            client.put(f'/api/patients/{patient_id}', json=update_data, headers=auth_headers)
            
            patient = Patient.query.get(patient_id)
            assert patient.active == False
    
    def test_update_patient_admitted_datetime(self, client, auth_headers):
        """Test updating patient admitted_datetime"""
        with client.application.app_context():
            # Create patient
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01'
            }
            
            create_response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            patient_id = create_response.get_json()['patient']['id']
            
            # Update admitted_datetime
            update_data = {
                'admitted': True,
                'admittedDatetime': '2024-01-20T14:30:00Z'
            }
            client.put(f'/api/patients/{patient_id}', json=update_data, headers=auth_headers)
            
            patient = Patient.query.get(patient_id)
            assert patient.admitted == True
            assert patient.admitted_datetime is not None
    
    def test_update_patient_notes(self, client, auth_headers):
        """Test updating patient notes"""
        with client.application.app_context():
            # Create patient
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'notes': 'Initial note'
            }
            
            create_response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            patient_id = create_response.get_json()['patient']['id']
            
            # Update notes
            update_data = {'notes': 'Updated note with more information'}
            client.put(f'/api/patients/{patient_id}', json=update_data, headers=auth_headers)
            
            patient = Patient.query.get(patient_id)
            assert patient.notes == 'Updated note with more information'
    
    def test_update_patient_date_of_birth(self, client, auth_headers):
        """Test updating patient date_of_birth"""
        with client.application.app_context():
            # Create patient
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'dateOfBirth': '1990-01-01'
            }
            
            create_response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            patient_id = create_response.get_json()['patient']['id']
            
            # Update date_of_birth
            update_data = {'dateOfBirth': '1985-06-15'}
            client.put(f'/api/patients/{patient_id}', json=update_data, headers=auth_headers)
            
            patient = Patient.query.get(patient_id)
            assert patient.date_of_birth == date(1985, 6, 15)
    
    def test_all_new_fields_in_response(self, client, auth_headers):
        """Test that all new fields are included in API response"""
        with client.application.app_context():
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'active': True,
                'admitted': True,
                'admittedDatetime': '2024-01-15T10:30:00Z',
                'notes': 'Test notes',
                'dateOfBirth': '1990-05-15'
            }
            
            create_response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            patient_id = create_response.get_json()['patient']['id']
            
            # Get patient
            response = client.get(f'/api/patients/{patient_id}', headers=auth_headers)
            assert response.status_code == 200
            
            patient_data = response.get_json()['patient']
            
            # Verify all fields are in response
            assert 'active' in patient_data
            assert patient_data['active'] == True
            assert 'admittedDatetime' in patient_data
            assert patient_data['admittedDatetime'] is not None
            assert 'notes' in patient_data
            assert patient_data['notes'] == 'Test notes'
            assert 'dateOfBirth' in patient_data
            assert patient_data['dateOfBirth'] == '1990-05-15'


