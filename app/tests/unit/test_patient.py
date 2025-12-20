import pytest
from app.models.patient import Patient
from app.services.patient_service import PatientService
from app import db

class TestPatientService:
    """Test cases for PatientService"""
    
    def test_create_patient(self, app):
        """Test patient creation"""
        with app.app_context():
            from app.models.user import User
            from app.models.role import Role
            
            # Create a user first
            role = Role.query.filter_by(name='clinician').first()
            if not role:
                role = Role(name='clinician', description='Clinician')
                db.session.add(role)
                db.session.commit()
            
            user = User(
                username='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User',
                role='clinician',
                role_id=role.id
            )
            user.set_password('TestPass123!@#')
            db.session.add(user)
            db.session.commit()
            
            patient_service = PatientService()
            patient_data = {
                'patientName': 'John Doe',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'dateOfBirth': '1990-01-15',
                'active': True
            }
            
            patient = patient_service.create_patient(patient_data, user.id)
            
            assert patient.patient_name == 'John Doe'
            assert patient.case_manager_name == 'Test CM'
            assert patient.phone_number == '555-1234'
            assert patient.facility_name == 'Test Facility'
            assert patient.active == True
            assert patient.created_by == user.id
    
    def test_create_patient_without_id(self, app):
        """Test patient creation without providing patient_id"""
        with app.app_context():
            from app.models.user import User
            from app.models.role import Role
            
            # Create a user first
            role = Role.query.filter_by(name='clinician').first()
            if not role:
                role = Role(name='clinician', description='Clinician')
                db.session.add(role)
                db.session.commit()
            
            user = User(
                username='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User',
                role='clinician',
                role_id=role.id
            )
            user.set_password('TestPass123!@#')
            db.session.add(user)
            db.session.commit()
            
            patient_service = PatientService()
            patient_data = {
                'patientName': 'Jane Smith',
                'caseManagerName': 'Test CM',
                'phoneNumber': '555-1234',
                'facilityName': 'Test Facility',
                'date': '2024-01-01',
                'dateOfBirth': '1985-05-20',
                'active': True
            }
            
            patient = patient_service.create_patient(patient_data, user.id)
            
            assert patient.patient_name == 'Jane Smith'
            assert patient.case_manager_name == 'Test CM'
            assert patient.active == True
    
    def test_update_patient(self, app):
        """Test patient update"""
        with app.app_context():
            patient_service = PatientService()
            patient_data = {
                'patient_id': 'PAT-2024-001',
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1990-01-15',
                'gender': 'Male',
                'status': 'active'
            }
            
            patient = patient_service.create_patient(patient_data, 1)
            
            update_data = {
                'first_name': 'Johnny',
                'phone': '+1234567890',
                'email': 'johnny.doe@example.com'
            }
            
            updated_patient = patient_service.update_patient(patient, update_data)
            
            assert updated_patient.first_name == 'Johnny'
            assert updated_patient.phone == '+1234567890'
            assert updated_patient.email == 'johnny.doe@example.com'
            assert updated_patient.last_name == 'Doe'  # Should remain unchanged
    
    def test_get_patients_with_pagination(self, app):
        """Test getting patients with pagination"""
        with app.app_context():
            patient_service = PatientService()
            
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
                patient_service.create_patient(patient_data, 1)
            
            # Test pagination
            patients, total = patient_service.get_patients(page=1, per_page=10)
            
            assert len(patients) == 10
            assert total == 15
            
            # Test second page
            patients, total = patient_service.get_patients(page=2, per_page=10)
            
            assert len(patients) == 5
            assert total == 15
    
    def test_get_patients_with_search(self, app):
        """Test getting patients with search filter"""
        with app.app_context():
            patient_service = PatientService()
            
            # Create patients with different names
            patient_data1 = {
                'patient_id': 'PAT-2024-001',
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1990-01-15',
                'gender': 'Male',
                'status': 'active'
            }
            
            patient_data2 = {
                'patient_id': 'PAT-2024-002',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'date_of_birth': '1985-05-20',
                'gender': 'Female',
                'status': 'active'
            }
            
            patient_service.create_patient(patient_data1, 1)
            patient_service.create_patient(patient_data2, 1)
            
            # Search by first name
            patients, total = patient_service.get_patients(search='John')
            assert len(patients) == 1
            assert patients[0].first_name == 'John'
            
            # Search by last name
            patients, total = patient_service.get_patients(search='Smith')
            assert len(patients) == 1
            assert patients[0].last_name == 'Smith'
    
    def test_get_patients_with_status_filter(self, app):
        """Test getting patients with status filter"""
        with app.app_context():
            patient_service = PatientService()
            
            # Create patients with different statuses
            patient_data1 = {
                'patient_id': 'PAT-2024-001',
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1990-01-15',
                'gender': 'Male',
                'status': 'active'
            }
            
            patient_data2 = {
                'patient_id': 'PAT-2024-002',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'date_of_birth': '1985-05-20',
                'gender': 'Female',
                'status': 'inactive'
            }
            
            patient_service.create_patient(patient_data1, 1)
            patient_service.create_patient(patient_data2, 1)
            
            # Filter by active status
            patients, total = patient_service.get_patients(status='active')
            assert len(patients) == 1
            assert patients[0].status == 'active'
            
            # Filter by inactive status
            patients, total = patient_service.get_patients(status='inactive')
            assert len(patients) == 1
            assert patients[0].status == 'inactive'
    
    def test_get_patient_by_id(self, app):
        """Test getting patient by ID"""
        with app.app_context():
            patient_service = PatientService()
            patient_data = {
                'patient_id': 'PAT-2024-001',
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1990-01-15',
                'gender': 'Male',
                'status': 'active'
            }
            
            created_patient = patient_service.create_patient(patient_data, 1)
            patient = patient_service.get_patient_by_id(created_patient.id)
            
            assert patient is not None
            assert patient.id == created_patient.id
            assert patient.patient_id == 'PAT-2024-001'
    
    def test_get_patient_by_patient_id(self, app):
        """Test getting patient by patient_id field"""
        with app.app_context():
            patient_service = PatientService()
            patient_data = {
                'patient_id': 'PAT-2024-001',
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1990-01-15',
                'gender': 'Male',
                'status': 'active'
            }
            
            patient_service.create_patient(patient_data, 1)
            patient = patient_service.get_patient_by_patient_id('PAT-2024-001')
            
            assert patient is not None
            assert patient.patient_id == 'PAT-2024-001'
    
    def test_delete_patient(self, app):
        """Test soft delete of patient"""
        with app.app_context():
            patient_service = PatientService()
            patient_data = {
                'patient_id': 'PAT-2024-001',
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1990-01-15',
                'gender': 'Male',
                'status': 'active'
            }
            
            patient = patient_service.create_patient(patient_data, 1)
            assert patient.status == 'active'
            
            deleted_patient = patient_service.delete_patient(patient)
            assert deleted_patient.status == 'inactive'
    
    def test_restore_patient(self, app):
        """Test restoring a deleted patient"""
        with app.app_context():
            patient_service = PatientService()
            patient_data = {
                'patient_id': 'PAT-2024-001',
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1990-01-15',
                'gender': 'Male',
                'status': 'active'
            }
            
            patient = patient_service.create_patient(patient_data, 1)
            patient_service.delete_patient(patient)
            assert patient.status == 'inactive'
            
            restored_patient = patient_service.restore_patient(patient)
            assert restored_patient.status == 'active'
