from app import db
from datetime import datetime

class HomeHealth(db.Model):
    """Model for storing home health agency information"""
    __tablename__ = 'home_health'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with users (backref defined in User model)
    # Users can have roles: admin, clinicians, case_manager
    
    def to_dict(self):
        """Convert home health agency to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'email': self.email,
            'phone_number': self.phone_number,
            'address': self.address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<HomeHealth {self.id}: {self.name}>'
