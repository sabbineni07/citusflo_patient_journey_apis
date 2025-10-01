from app import db
from app.models.user import User
from datetime import datetime

class AuthService:
    """Service class for authentication operations"""
    
    def create_user(self, user_data):
        """Create a new user"""
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            role=user_data.get('role', 'user')
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
        for key, value in user_data.items():
            if hasattr(user, key) and key not in ['id', 'created_at', 'updated_at']:
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
