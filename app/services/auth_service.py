from app import db
from app.models.user import User
from app.models.facility import Facility
from datetime import datetime

class AuthService:
    """Service class for authentication operations"""
    
    def create_user(self, user_data):
        """Create a new user"""
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
            
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            role=user_data.get('role', 'user'),
            facility_id=facility_id,
            is_active=user_data.get('is_active', True)
        )
        
        # Set password
        user.set_password(user_data['password'])
        
        # Save to database
        db.session.add(user)
        db.session.commit()
        
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
