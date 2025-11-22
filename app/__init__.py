from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Use Redis in production: "redis://localhost:6379"
)

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/patient_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
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
    from app.routes.auth import auth_bp
    from app.routes.patients import patients_bp
    from app.routes.case_manager_records import case_manager_records_bp
    from app.routes.facilities import facilities_bp
    from app.routes.webauthn import webauthn_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(patients_bp, url_prefix='/api/patients')
    app.register_blueprint(case_manager_records_bp, url_prefix='/api/case-manager-records')
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
        
        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@hospital.com',
                first_name='Admin',
                last_name='User',
                role='admin'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created: username=admin, password=admin123")
        
        print("Database initialized successfully!")
    
    return app

# Create the app instance for Gunicorn
app = create_app()
