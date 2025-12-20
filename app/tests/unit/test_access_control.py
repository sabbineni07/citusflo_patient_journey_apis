import pytest
from app.utils.access_control import (
    filter_patients_by_access,
    can_access_patient,
    can_modify_patient,
    can_create_patient,
    can_delete_patient
)
from app.models.user import User
from app.models.patient import Patient
from app.models.role import Role
from app.models.facility import Facility
from app.models.home_health import HomeHealth
from app import db
from datetime import datetime


@pytest.mark.unit
class TestAccessControl:
    """Unit tests for access control functions"""
    
    def test_super_admin_can_access_all_patients(self, app):
        """Test that super_admin can access all patients"""
        with app.app_context():
            # Create roles (use get_or_create to avoid duplicates)
            super_admin_role = Role.get_or_create('super_admin', 'Super Admin')
            
            # Create super admin user
            super_admin = User(
                username='superadmin',
                email='superadmin@example.com',
                first_name='Super',
                last_name='Admin',
                role='super_admin',
                role_id=super_admin_role.id
            )
            super_admin.set_password('Password123!@#')
            db.session.add(super_admin)
            db.session.commit()
            
            # Create patients
            patient1 = Patient(
                patient_name='Patient 1',
                case_manager_name='CM 1',
                phone_number='555-0001',
                facility_name='Facility 1',
                date=datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
                created_by=super_admin.id
            )
            patient2 = Patient(
                patient_name='Patient 2',
                case_manager_name='CM 2',
                phone_number='555-0002',
                facility_name='Facility 2',
                date=datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
                created_by=super_admin.id
            )
            db.session.add_all([patient1, patient2])
            db.session.commit()
            
            # Test access
            query = Patient.query
            filtered_query = filter_patients_by_access(super_admin, query)
            accessible_patients = filtered_query.all()
            
            # Super admin should see all patients
            assert len(accessible_patients) >= 2
    
    def test_clinician_can_access_own_organization_patients(self, app):
        """Test that clinicians can only access patients from their organization"""
        with app.app_context():
            # Create roles (use get_or_create to avoid duplicates)
            from app.models.role import Role
            clinician_role = Role.get_or_create('clinician', 'Clinician')
            
            # Create home health agency
            home_health = HomeHealth(name='Test Home Health')
            db.session.add(home_health)
            db.session.commit()
            
            # Create clinician user
            clinician = User(
                username='clinician',
                email='clinician@example.com',
                first_name='Test',
                last_name='Clinician',
                role='clinician',
                role_id=clinician_role.id,
                home_health_id=home_health.id
            )
            clinician.set_password('Password123!@#')
            db.session.add(clinician)
            db.session.commit()
            
            # Create patients - one from same org, one from different org
            patient1 = Patient(
                patient_name='Patient 1',
                case_manager_name='CM 1',
                phone_number='555-0001',
                facility_name='Facility 1',
                date=datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
                home_health_id=home_health.id,
                created_by=clinician.id
            )
            
            other_home_health = HomeHealth(name='Other Home Health')
            db.session.add(other_home_health)
            db.session.commit()
            
            patient2 = Patient(
                patient_name='Patient 2',
                case_manager_name='CM 2',
                phone_number='555-0002',
                facility_name='Facility 2',
                date=datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
                home_health_id=other_home_health.id,
                created_by=clinician.id
            )
            db.session.add_all([patient1, patient2])
            db.session.commit()
            
            # Test access
            query = Patient.query
            filtered_query = filter_patients_by_access(clinician, query)
            accessible_patients = filtered_query.all()
            
            # Clinician should only see patients from their organization
            assert len(accessible_patients) >= 1
            assert all(p.home_health_id == home_health.id for p in accessible_patients)
    
    def test_can_access_patient_super_admin(self, app):
        """Test that super_admin can access any patient"""
        with app.app_context():
            # Create roles (use get_or_create to avoid duplicates)
            super_admin_role = Role.get_or_create('super_admin', 'Super Admin')
            
            # Create super admin user
            super_admin = User(
                username='superadmin',
                email='superadmin@example.com',
                first_name='Super',
                last_name='Admin',
                role='super_admin',
                role_id=super_admin_role.id
            )
            super_admin.set_password('Password123!@#')
            db.session.add(super_admin)
            db.session.commit()
            
            # Create patient
            patient = Patient(
                patient_name='Test Patient',
                case_manager_name='CM 1',
                phone_number='555-0001',
                facility_name='Facility 1',
                date=datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
                created_by=super_admin.id
            )
            db.session.add(patient)
            db.session.commit()
            
            # Test access
            assert can_access_patient(super_admin, patient) == True
    
    def test_can_modify_patient_permissions(self, app):
        """Test patient modification permissions"""
        with app.app_context():
            # Create roles (use get_or_create to avoid duplicates)
            admin_role = Role.get_or_create('admin', 'Admin')
            clinician_role = Role.get_or_create('clinician', 'Clinician')
            case_manager_role = Role.get_or_create('case_manager', 'Case Manager')
            
            # Create users
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                role='admin',
                role_id=admin_role.id
            )
            admin.set_password('Password123!@#')
            
            clinician = User(
                username='clinician',
                email='clinician@example.com',
                first_name='Test',
                last_name='Clinician',
                role='clinician',
                role_id=clinician_role.id
            )
            clinician.set_password('Password123!@#')
            
            case_manager = User(
                username='casemgr',
                email='casemgr@example.com',
                first_name='Case',
                last_name='Manager',
                role='case_manager',
                role_id=case_manager_role.id
            )
            case_manager.set_password('Password123!@#')
            
            db.session.add_all([admin, clinician, case_manager])
            db.session.commit()
            
            # Create patient
            patient = Patient(
                patient_name='Test Patient',
                case_manager_name='CM 1',
                phone_number='555-0001',
                facility_name='Facility 1',
                date=datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
                created_by=admin.id
            )
            db.session.add(patient)
            db.session.commit()
            
            # Test permissions
            assert can_modify_patient(admin, patient) == True
            assert can_modify_patient(clinician, patient) == True
            assert can_modify_patient(case_manager, patient) == False  # Case managers can't modify
    
    def test_can_create_patient_permissions(self, app):
        """Test patient creation permissions"""
        with app.app_context():
            # Create roles (use get_or_create to avoid duplicates)
            admin_role = Role.get_or_create('admin', 'Admin')
            clinician_role = Role.get_or_create('clinician', 'Clinician')
            case_manager_role = Role.get_or_create('case_manager', 'Case Manager')
            
            # Create users
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                role='admin',
                role_id=admin_role.id
            )
            admin.set_password('Password123!@#')
            
            clinician = User(
                username='clinician',
                email='clinician@example.com',
                first_name='Test',
                last_name='Clinician',
                role='clinician',
                role_id=clinician_role.id
            )
            clinician.set_password('Password123!@#')
            
            case_manager = User(
                username='casemgr',
                email='casemgr@example.com',
                first_name='Case',
                last_name='Manager',
                role='case_manager',
                role_id=case_manager_role.id
            )
            case_manager.set_password('Password123!@#')
            
            db.session.add_all([admin, clinician, case_manager])
            db.session.commit()
            
            # Test permissions
            assert can_create_patient(admin) == True
            assert can_create_patient(clinician) == True
            assert can_create_patient(case_manager) == False  # Case managers can't create
    
    def test_can_delete_patient_permissions(self, app):
        """Test patient deletion permissions"""
        with app.app_context():
            # Create roles (use get_or_create to avoid duplicates)
            from app.models.role import Role
            admin_role = Role.get_or_create('admin', 'Admin')
            clinician_role = Role.get_or_create('clinician', 'Clinician')
            
            # Create users
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                role='admin',
                role_id=admin_role.id
            )
            admin.set_password('Password123!@#')
            
            clinician = User(
                username='clinician',
                email='clinician@example.com',
                first_name='Test',
                last_name='Clinician',
                role='clinician',
                role_id=clinician_role.id
            )
            clinician.set_password('Password123!@#')
            
            db.session.add_all([admin, clinician])
            db.session.commit()
            
            # Create patient
            patient = Patient(
                patient_name='Test Patient',
                case_manager_name='CM 1',
                phone_number='555-0001',
                facility_name='Facility 1',
                date=datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
                created_by=admin.id
            )
            db.session.add(patient)
            db.session.commit()
            
            # Test permissions
            assert can_delete_patient(admin) == True
            assert can_delete_patient(clinician) == False  # Only admins can delete

