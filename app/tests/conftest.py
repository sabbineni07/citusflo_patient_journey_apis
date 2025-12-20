import pytest
import os
from app import create_app, db
from app.models.user import User
from app.models.patient import Patient

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    import os
    # Force test database configuration
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    os.environ['FLASK_ENV'] = 'testing'
    
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key",
        "SECRET_KEY": "test-secret-key"
    })
    
    with app.app_context():
        db.create_all()
        # Seed roles for tests
        from app.models.role import Role
        Role.get_or_create('super_admin', 'Super Administrator')
        Role.get_or_create('admin', 'Administrator')
        Role.get_or_create('clinician', 'Clinician')
        Role.get_or_create('case_manager', 'Case Manager')
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth_headers(client):
    """Get authentication headers for testing."""
    # Create a test user
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPass123!@#',  # HIPAA compliant password
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    # Register user
    client.post('/api/auth/register', json=user_data)
    
    # Login and get token
    login_response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'TestPass123!@#'  # HIPAA compliant password
    })
    
    token = login_response.json['access_token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def admin_headers(client):
    """Get admin authentication headers for testing."""
    from app.models.role import Role
    
    # Create admin user with super_admin role for testing
    with client.application.app_context():
        # Get or create super_admin role
        super_admin_role = Role.query.filter_by(name='super_admin').first()
        if not super_admin_role:
            super_admin_role = Role(name='super_admin', description='Super Administrator')
            db.session.add(super_admin_role)
            db.session.commit()
        
        admin_user = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            role='super_admin',  # Backward compatibility string field
            role_id=super_admin_role.id  # Proper role relationship
        )
        admin_user.set_password('AdminPass123!@#')  # HIPAA compliant password
        db.session.add(admin_user)
        db.session.commit()
    
    # Login and get token
    login_response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'AdminPass123!@#'  # HIPAA compliant password
    })
    
    token = login_response.json['access_token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def sample_patient_data():
    """Sample patient data for testing."""
    return {
        'patient_id': 'PAT-2024-001',
        'first_name': 'John',
        'last_name': 'Doe',
        'date_of_birth': '1990-01-15',
        'gender': 'Male',
        'phone': '+1234567890',
        'email': 'john.doe@example.com',
        'address': '123 Main St, City, State 12345',
        'emergency_contact_name': 'Jane Doe',
        'emergency_contact_phone': '+1234567891',
        'medical_history': 'No significant medical history',
        'allergies': 'None known',
        'current_medications': 'None',
        'insurance_provider': 'Health Insurance Co',
        'insurance_number': 'INS123456789',
        'status': 'active'
    }
