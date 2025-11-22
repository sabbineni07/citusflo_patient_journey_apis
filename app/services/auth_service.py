from app import db
from app.models.user import User
from app.models.facility import Facility
from app.models.home_health import HomeHealth
from app.models.role import Role
from datetime import datetime
from sqlalchemy.exc import IntegrityError

class AuthService:
    """Service class for authentication operations"""
    
    def create_user(self, user_data, created_by_user=None):
        """Create a new user
        
        Args:
            user_data: Dictionary containing user data
            created_by_user: Optional User object who is creating this user (for inheritance)
        """
        # Handle facility creation/assignment
        facility_id = user_data.get('facility_id')
        facility_name = user_data.get('facility_name')
        
        # If facility_name is provided, get or create the facility
        if facility_name:
            facility = Facility.get_or_create(
                name=facility_name,
                address=user_data.get('facility_address'),
                phone=user_data.get('facility_phone')
            )
            facility_id = facility.id
        elif facility_id and str(facility_id).strip():
            # Handle facility_id conversion if provided
            try:
                facility_id = int(facility_id)
            except (ValueError, TypeError):
                facility_id = None
        else:
            facility_id = None
            
        # Handle home_health creation/assignment
        home_health_id = user_data.get('home_health_id')
        if home_health_id and str(home_health_id).strip():
            try:
                home_health_id = int(home_health_id)
                # Verify home_health exists
                home_health = HomeHealth.query.get(home_health_id)
                if not home_health:
                    home_health_id = None
            except (ValueError, TypeError):
                home_health_id = None
        else:
            # If home_health_id not provided and created_by_user is an admin, inherit it
            if created_by_user and created_by_user.home_health_id:
                # Inherit from admin user if they have a home_health_id
                home_health_id = created_by_user.home_health_id
            else:
                home_health_id = None
        
        # Handle role assignment - use role_id or role name
        role_id = None
        if user_data.get('role_id'):
            try:
                role_id = int(user_data['role_id'])
                # Verify role exists
                role = Role.query.get(role_id)
                if not role:
                    role_id = None
            except (ValueError, TypeError):
                role_id = None
        elif user_data.get('role'):
            # Get role by name
            role = Role.query.filter_by(name=user_data['role']).first()
            if role:
                role_id = role.id
        
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            role_id=role_id,
            facility_id=facility_id,
            home_health_id=home_health_id,
            is_active=user_data.get('is_active', True)
        )
        
        # Set password
        user.set_password(user_data['password'])
        
        # Save to database
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError as e:
            # Rollback the session on integrity error
            db.session.rollback()
            # Re-raise to let the route handle it
            raise
        
        return user
    
    def authenticate_user(self, username, password):
        """Authenticate user with username and password"""
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            return user
        
        return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        return User.query.get(user_id)
    
    def get_user_by_username(self, username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()
    
    def get_user_by_email(self, email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    def update_user(self, user, user_data):
        """Update user information"""
        # Handle facility updates
        if 'facility_name' in user_data:
            facility_name = user_data['facility_name']
            if facility_name:
                facility = Facility.get_or_create(
                    name=facility_name,
                    address=user_data.get('facility_address'),
                    phone=user_data.get('facility_phone')
                )
                user.facility_id = facility.id
            else:
                user.facility_id = None
        
        # Handle other field updates
        for key, value in user_data.items():
            if hasattr(user, key) and key not in ['id', 'created_at', 'updated_at', 'facility_name', 'facility_address', 'facility_phone']:
                if key == 'facility_id':
                    # Handle facility_id conversion
                    if value and str(value).strip():
                        try:
                            setattr(user, key, int(value))
                        except (ValueError, TypeError):
                            setattr(user, key, None)
                    else:
                        setattr(user, key, None)
                else:
                    setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return user
    
    def deactivate_user(self, user):
        """Deactivate a user account"""
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return user
    
    def activate_user(self, user):
        """Activate a user account"""
        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return user
