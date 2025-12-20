import pytest
from app.models.patient import Patient
from app.models.patient_form import PatientForm
from app.models.user import User
from app.models.role import Role
from app import db


@pytest.mark.integration
class TestPatientForms:
    """Integration tests for patient forms functionality"""
    
    def test_create_patient_with_forms(self, client, auth_headers):
        """Test creating a patient with forms"""
        with client.application.app_context():
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'forms': [
                    {
                        'formId': 1,
                        'formType': 'intake',
                        'formData': {'field1': 'value1', 'field2': 'value2'}
                    }
                ]
            }
            
            response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            assert response.status_code == 201
            
            patient_id = response.get_json()['patient']['id']
            
            # Verify form was created
            patient = Patient.query.get(patient_id)
            forms = patient.get_latest_forms()
            
            assert len(forms) == 1
            assert forms[0].form_type == 'intake'
            assert forms[0].form_id == 1
            assert forms[0].form_data == {'field1': 'value1', 'field2': 'value2'}
    
    def test_update_patient_forms_creates_new_entry(self, client, auth_headers):
        """Test that updating forms creates a new entry (versioning)"""
        with client.application.app_context():
            # Create patient with form
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'forms': [
                    {
                        'formId': 1,
                        'formType': 'intake',
                        'formData': {'field1': 'value1'}
                    }
                ]
            }
            
            create_response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            patient_id = create_response.get_json()['patient']['id']
            
            # Get initial form count
            patient = Patient.query.get(patient_id)
            initial_count = PatientForm.query.filter_by(patient_id=patient_id).count()
            
            # Update form with same form_id
            update_data = {
                'forms': [
                    {
                        'formId': 1,
                        'formType': 'intake',
                        'formData': {'field1': 'updated_value'}
                    }
                ]
            }
            
            client.put(f'/api/patients/{patient_id}', json=update_data, headers=auth_headers)
            
            # Verify new entry was created (versioning)
            new_count = PatientForm.query.filter_by(patient_id=patient_id).count()
            assert new_count == initial_count + 1
            
            # Verify latest form has updated data
            latest_forms = patient.get_latest_forms()
            intake_form = [f for f in latest_forms if f.form_type == 'intake' and f.form_id == 1][0]
            assert intake_form.form_data == {'field1': 'updated_value'}
    
    def test_get_latest_forms_returns_most_recent(self, client, auth_headers):
        """Test that get_latest_forms returns only the most recent form per form_id"""
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
            
            # Create multiple versions of the same form
            patient = Patient.query.get(patient_id)
            user = User.query.first()
            
            # Create form version 1
            form1 = PatientForm(
                patient_id=patient_id,
                form_id=1,
                form_type='intake',
                form_data={'version': 1},
                created_by=user.id if user else None
            )
            db.session.add(form1)
            db.session.commit()
            
            # Create form version 2 (more recent)
            form2 = PatientForm(
                patient_id=patient_id,
                form_id=1,
                form_type='intake',
                form_data={'version': 2},
                created_by=user.id if user else None
            )
            db.session.add(form2)
            db.session.commit()
            
            # Get latest forms
            latest_forms = patient.get_latest_forms()
            
            # Should only return one form with form_id=1 (the most recent)
            intake_forms = [f for f in latest_forms if f.form_id == 1]
            assert len(intake_forms) == 1
            assert intake_forms[0].form_data == {'version': 2}
    
    def test_multiple_form_types(self, client, auth_headers):
        """Test patient with multiple different form types"""
        with client.application.app_context():
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'forms': [
                    {
                        'formId': 1,
                        'formType': 'intake',
                        'formData': {'intake_field': 'value1'}
                    },
                    {
                        'formId': 2,
                        'formType': 'assessment',
                        'formData': {'assessment_field': 'value2'}
                    },
                    {
                        'formId': 3,
                        'formType': 'discharge',
                        'formData': {'discharge_field': 'value3'}
                    }
                ]
            }
            
            response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            assert response.status_code == 201
            
            patient_id = response.get_json()['patient']['id']
            patient = Patient.query.get(patient_id)
            forms = patient.get_latest_forms()
            
            # Should have 3 forms
            assert len(forms) == 3
            
            # Verify all form types are present
            form_types = [f.form_type for f in forms]
            assert 'intake' in form_types
            assert 'assessment' in form_types
            assert 'discharge' in form_types
    
    def test_forms_in_patient_response(self, client, auth_headers):
        """Test that forms are included in patient API response"""
        with client.application.app_context():
            patient_data = {
                'patientName': 'Test Patient',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'forms': [
                    {
                        'formId': 1,
                        'formType': 'intake',
                        'formData': {'field1': 'value1'}
                    }
                ]
            }
            
            create_response = client.post('/api/patients/', json=patient_data, headers=auth_headers)
            patient_id = create_response.get_json()['patient']['id']
            
            # Get patient
            response = client.get(f'/api/patients/{patient_id}', headers=auth_headers)
            assert response.status_code == 200
            
            patient_data = response.get_json()['patient']
            
            # Verify forms are in response
            assert 'forms' in patient_data
            assert len(patient_data['forms']) == 1
            assert patient_data['forms'][0]['formType'] == 'intake'
            assert patient_data['forms'][0]['formId'] == 1
            assert 'createdBy' in patient_data['forms'][0]
            assert 'createdAt' in patient_data['forms'][0]


