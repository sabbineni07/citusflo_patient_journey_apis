from app import db, bcrypt
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=True)  # Kept for backward compatibility, deprecated
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=True)
    home_health_id = db.Column(db.Integer, db.ForeignKey('home_health.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with patients
    patients = db.relationship('Patient', backref='created_by_user', lazy=True)
    
    # Relationship with facility
    facility = db.relationship('Facility', backref='users', lazy=True)
    
    # Relationship with home health agency
    home_health = db.relationship('HomeHealth', backref='users', lazy=True)
    
    # Relationship with role
    role_ref = db.relationship('Role', backref='users', lazy=True)
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches the hash"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @property
    def has_webauthn(self):
        """Check if user has any WebAuthn credentials enabled"""
        # Check if user has any WebAuthn credentials
        # Uses the backref relationship defined in WebAuthnCredential model
        return len(self.webauthn_credentials) > 0
    
    @property
    def role_name(self):
        """Get role name from role relationship (backward compatible)"""
        if self.role_ref:
            return self.role_ref.name
        # Fallback to old role string for backward compatibility
        return self.role
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role_name,  # Use role_name property for backward compatibility
            'role_id': self.role_id,
            'role_name': self.role_name,
            'facility_id': self.facility_id,
            'facility_name': self.facility.name if self.facility else None,
            'home_health_id': self.home_health_id,
            'home_health_name': self.home_health.name if self.home_health else None,
            'is_active': self.is_active,
            'has_webauthn': self.has_webauthn,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'
