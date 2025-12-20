from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Custom key function to exclude OPTIONS requests from rate limiting
def rate_limit_key_func():
    """Custom key function that excludes OPTIONS requests from rate limiting"""
    if request.method == 'OPTIONS':
        # Return None to skip rate limiting for OPTIONS requests
        return None
    return get_remote_address()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()

# Get rate limits from environment or use defaults
# Development: More permissive limits
# Production: Stricter limits
flask_env = os.getenv('FLASK_ENV', 'development')
if flask_env == 'production':
    default_limits = os.getenv('RATE_LIMIT', "1000 per day, 200 per hour, 60 per minute")
else:
    # Development: Much more permissive
    default_limits = os.getenv('RATE_LIMIT', "10000 per day, 1000 per hour, 200 per minute")

limiter = Limiter(
    key_func=rate_limit_key_func,
    default_limits=[default_limits],
    storage_uri="memory://"  # Use Redis in production: "redis://localhost:6379"
)

def create_app():
    app = Flask(__name__)
    
    # Configuration
    # Configuration - All secrets MUST come from environment variables
    # Use secure defaults that fail fast if not configured properly
    secret_key = os.getenv('SECRET_KEY')
    jwt_secret_key = os.getenv('JWT_SECRET_KEY')
    database_url = os.getenv('DATABASE_URL')
    
    # In production, require all secrets to be set via environment variables
    if flask_env == 'production':
        if not secret_key:
            raise ValueError('SECRET_KEY environment variable is required in production')
        if not jwt_secret_key:
            raise ValueError('JWT_SECRET_KEY environment variable is required in production')
        if not database_url:
            raise ValueError('DATABASE_URL environment variable is required in production')
    else:
        # Development: Use weak defaults with warnings (NOT for production use)
        if not secret_key:
            import warnings
            warnings.warn('SECRET_KEY not set, using insecure default for development only', UserWarning)
            secret_key = 'dev-secret-key-INSECURE-DO-NOT-USE-IN-PRODUCTION'
        if not jwt_secret_key:
            import warnings
            warnings.warn('JWT_SECRET_KEY not set, using insecure default for development only', UserWarning)
            jwt_secret_key = 'dev-jwt-secret-key-INSECURE-DO-NOT-USE-IN-PRODUCTION'
        if not database_url:
            # Development default - should use .env file
            database_url = 'postgresql://postgres:CHANGE_ME@localhost:5432/patient_db'
            import warnings
            warnings.warn('DATABASE_URL not set, using default. Set via .env file for proper configuration', UserWarning)
    
    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = jwt_secret_key
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if os.getenv('FLASK_ENV') == 'production' else logging.DEBUG,
        format='%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    
    # Configure CORS
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:4200,http://localhost:3000,http://127.0.0.1:4200,http://127.0.0.1:3000').split(',')
    # Clean up origins (remove whitespace)
    cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
    
    # Log CORS configuration in development
    if os.getenv('FLASK_ENV') != 'production':
        logging.info(f'CORS Origins: {cors_origins}')
    
    CORS(app, 
         origins=cors_origins,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         expose_headers=['Content-Type', 'Authorization'],
         supports_credentials=True,
         max_age=3600)  # Cache preflight requests for 1 hour
    
    # Register blueprints
    # IMPORTANT: Register patient_forms_bp BEFORE patients_bp so more specific routes match first
    from app.routes.auth import auth_bp
    from app.routes.patients import patients_bp
    from app.routes.patient_forms import patient_forms_bp
    from app.routes.facilities import facilities_bp
    from app.routes.webauthn import webauthn_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(patient_forms_bp, url_prefix='/api/patients')  # Register BEFORE patients_bp for route matching
    app.register_blueprint(patients_bp, url_prefix='/api/patients')
    app.register_blueprint(facilities_bp, url_prefix='/api/facilities')
    app.register_blueprint(webauthn_bp, url_prefix='/api/auth/webauthn')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'patient-api'}, 200
    
    # CLI commands
    @app.cli.command()
    def init_db():
        """Initialize the database with sample data"""
        from app.models.user import User
        
        db.create_all()
        
        # Seed roles first (inline to avoid circular dependencies)
        from app.models.role import Role
        predefined_roles = [
            {'name': 'super_admin', 'description': 'Super Administrator with full system access and management'},
            {'name': 'admin', 'description': 'Administrator with full system access'},
            {'name': 'clinician', 'description': 'Clinical staff member'},
            {'name': 'case_manager', 'description': 'Case manager responsible for patient coordination'}
        ]
        for role_data in predefined_roles:
            Role.get_or_create(role_data['name'], role_data['description'])
        print("✅ Roles seeded successfully")
        
        # Create default super admin user if it doesn't exist
        admin_user = User.query.filter_by(username='citusflo_admin').first()
        if not admin_user:
            # Get super_admin role_id
            super_admin_role = Role.query.filter_by(name='super_admin').first()
            if not super_admin_role:
                # If super_admin role doesn't exist, create it
                super_admin_role = Role.get_or_create('super_admin', 'Super Administrator with full system access and management')

            # Get admin password from environment variable or generate a secure random one
            admin_password = os.getenv('ADMIN_PASSWORD')
            if not admin_password:
                # Generate a secure random password if not provided
                import secrets
                import string
                # Generate a 20-character password with complexity requirements
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                admin_password = ''.join(secrets.choice(alphabet) for _ in range(20))
                print("⚠️  WARNING: ADMIN_PASSWORD not set in environment variables")
                print(f"⚠️  Generated temporary admin password: {admin_password}")
                print("⚠️  IMPORTANT: Set ADMIN_PASSWORD environment variable and change password after first login!")
            else:
                print("✅ Using ADMIN_PASSWORD from environment variable")

            admin_user = User(
                username='citusflo_admin',
                email='account@citusflo.com',
                first_name='CitusFlo',
                last_name='Admin',
                role='super_admin',  # Kept for backward compatibility
                role_id=super_admin_role.id  # Set role_id for proper role relationship
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Super admin user created: username=citusflo_admin")
            print(f"Super admin user role_id: {super_admin_role.id}")
            if os.getenv('ADMIN_PASSWORD'):
                print("⚠️  Password set from ADMIN_PASSWORD environment variable (not displayed for security)")
            else:
                print(f"⚠️  Temporary password: {admin_password} (CHANGE THIS IMMEDIATELY!)")
        
        print("Database initialized successfully!")
    
    @app.cli.command()
    def cleanup_database():
        """Clean up all database tables, keeping only the default citusflo_admin user and roles"""
        from app.models.patient import Patient
        from app.models.user import User
        from app.models.facility import Facility
        from app.models.home_health import HomeHealth
        from app.models.hospital import Hospital
        from app.models.webauthn_credential import WebAuthnCredential
        from sqlalchemy import text
        
        print("🧹 Starting database cleanup...")
        print("   This will delete all data except the default 'citusflo_admin' user and roles")
        
        try:
            # Get the default user to preserve
            default_user = User.query.filter_by(username='citusflo_admin').first()
            default_user_id = default_user.id if default_user else None
            
            if not default_user:
                print("⚠️  Warning: Default user 'citusflo_admin' not found. Proceeding with cleanup anyway.")
            
            # 1. Delete all patients (has foreign keys to users, facilities, home_health)
            patient_count = Patient.query.count()
            Patient.query.delete()
            print(f"   ✅ Deleted {patient_count} patient records")
            
            # 2. Delete all WebAuthn credentials (has foreign key to users)
            webauthn_count = WebAuthnCredential.query.count()
            WebAuthnCredential.query.delete()
            print(f"   ✅ Deleted {webauthn_count} WebAuthn credential records")
            
            # 3. Reset all users' facility_id and home_health_id to avoid foreign key violations
            db.session.execute(text("UPDATE users SET facility_id = NULL, home_health_id = NULL"))
            print(f"   ✅ Reset all users' facility_id and home_health_id")
            
            # 4. Delete all facilities (has foreign key to hospitals)
            facility_count = Facility.query.count()
            Facility.query.delete()
            print(f"   ✅ Deleted {facility_count} facility records")
            
            # 5. Delete all junction table entries (home_health_hospitals)
            db.session.execute(text("DELETE FROM home_health_hospitals"))
            print(f"   ✅ Deleted home_health_hospitals junction table entries")
            
            # 6. Delete all hospitals
            hospital_count = Hospital.query.count()
            Hospital.query.delete()
            print(f"   ✅ Deleted {hospital_count} hospital records")
            
            # 7. Delete all home health agencies
            home_health_count = HomeHealth.query.count()
            HomeHealth.query.delete()
            print(f"   ✅ Deleted {home_health_count} home health agency records")
            
            # 8. Delete all users except the default user
            if default_user_id:
                user_count = User.query.filter(User.id != default_user_id).count()
                User.query.filter(User.id != default_user_id).delete()
                print(f"   ✅ Deleted {user_count} user records (kept citusflo_admin)")
            else:
                user_count = User.query.count()
                User.query.delete()
                print(f"   ⚠️  Deleted {user_count} user records (default user not found)")
            
            # Commit all changes
            db.session.commit()
            
            print("✅ Database cleanup completed successfully!")
            print(f"   Default user 'citusflo_admin' preserved: {'Yes' if default_user else 'No'}")
            print("   Roles table preserved (required for system operation)")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during database cleanup: {e}")
            import traceback
            traceback.print_exc()
            import sys
            sys.exit(1)
    
    @app.cli.command()
    def seed_roles():
        """Seed/rebuild the roles table with predefined roles
        
        IMPORTANT: This preserves role IDs to maintain foreign key relationships.
        If a role is missing, it will be recreated with the same ID.
        """
        from app.models.role import Role
        from app.models.user import User
        from sqlalchemy.exc import IntegrityError
        
        # Define the predefined roles with their standard IDs
        # These IDs are stable to preserve foreign key relationships
        predefined_roles = [
            {
                'id': 1,
                'name': 'super_admin',
                'description': 'Super Administrator with full system access and management'
            },
            {
                'id': 2,
                'name': 'admin',
                'description': 'Administrator with full system access'
            },
            {
                'id': 3,
                'name': 'clinician',
                'description': 'Clinical staff member'
            },
            {
                'id': 4,
                'name': 'case_manager',
                'description': 'Case manager responsible for patient coordination'
            }
        ]
        
        created_count = 0
        updated_count = 0
        existing_count = 0
        skipped_count = 0
        
        for role_data in predefined_roles:
            role_id = role_data['id']
            role_name = role_data['name']
            
            # Check if role exists by ID
            role_by_id = Role.query.get(role_id)
            
            # Check if role exists by name (might have different ID)
            role_by_name = Role.query.filter_by(name=role_name).first()
            
            if role_by_id:
                # Role with correct ID exists
                if role_by_id.name != role_name:
                    # ID exists but name doesn't match - this shouldn't happen with predefined roles
                    print(f"⚠️  WARNING: Role ID {role_id} exists but name is '{role_by_id.name}' (expected '{role_name}')")
                    # Don't update - might be intentional custom role
                    skipped_count += 1
                else:
                    # Update description if it changed
                    if role_by_id.description != role_data['description']:
                        role_by_id.description = role_data['description']
                        updated_count += 1
                        print(f"🔄 Updated role: {role_name} (ID: {role_id})")
                    else:
                        existing_count += 1
                        print(f"✓ Role already exists: {role_name} (ID: {role_id})")
            elif role_by_name:
                # Role exists with different ID - check if users are using it
                users_with_role = User.query.filter_by(role_id=role_by_name.id).count()
                if users_with_role > 0:
                    print(f"⚠️  WARNING: Role '{role_name}' exists with ID {role_by_name.id} (expected {role_id})")
                    print(f"   - {users_with_role} users are assigned to this role")
                    print(f"   - Keeping existing ID to preserve relationships")
                    # Update description but keep existing ID
                    if role_by_name.description != role_data['description']:
                        role_by_name.description = role_data['description']
                        updated_count += 1
                    skipped_count += 1
                else:
                    # No users using it, can safely delete and recreate with correct ID
                    print(f"🔄 Recreating role '{role_name}' with correct ID {role_id} (was {role_by_name.id})")
                    db.session.delete(role_by_name)
                    role = Role(id=role_id, name=role_name, description=role_data['description'])
                    db.session.add(role)
                    created_count += 1
            else:
                # Role doesn't exist - create with predefined ID
                try:
                    # Check if ID is already taken by a different role
                    existing_role_at_id = Role.query.get(role_id)
                    if existing_role_at_id:
                        print(f"⚠️  WARNING: Cannot create role '{role_name}' with ID {role_id} - ID already taken by '{existing_role_at_id.name}'")
                        skipped_count += 1
                    else:
                        # Create role with explicit ID to preserve foreign keys
                        role = Role(id=role_id, name=role_name, description=role_data['description'])
                        db.session.add(role)
                        created_count += 1
                        print(f"✅ Created role: {role_name} (ID: {role_id})")
                except IntegrityError as e:
                    print(f"❌ ERROR: Failed to create role '{role_name}': {e}")
                    db.session.rollback()
                    skipped_count += 1
        
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            print(f"\n❌ ERROR: Failed to commit roles: {e}")
            print("   This might be due to ID conflicts. Please check the database.")
            return
        
        print(f"\n📊 Roles Summary:")
        print(f"  - Created: {created_count}")
        print(f"  - Updated: {updated_count}")
        print(f"  - Existing: {existing_count}")
        print(f"  - Skipped: {skipped_count}")
        print(f"  - Total: {len(predefined_roles)}")
        
        # Verify all roles exist
        all_exist = True
        for role_data in predefined_roles:
            role = Role.query.get(role_data['id'])
            if not role or role.name != role_data['name']:
                print(f"  ⚠️  Missing or incorrect: {role_data['name']}")
                all_exist = False
        
        if all_exist:
            print("✅ All predefined roles exist with correct IDs!")
        
        return created_count, updated_count, existing_count
    
    # Auto-seed roles on app startup (if enabled via environment variable)
    if os.getenv('AUTO_SEED_ROLES', 'false').lower() == 'true':
        with app.app_context():
            try:
                seed_roles()
            except Exception as e:
                logging.warning(f"Failed to auto-seed roles on startup: {e}")
    
    return app

# Create the app instance for Gunicorn
app = create_app()
