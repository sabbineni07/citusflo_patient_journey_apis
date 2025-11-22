from app import db
from datetime import datetime

class Role(db.Model):
    """Model for storing user roles"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with users (backref defined in User model)
    
    def to_dict(self):
        """Convert role to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_by_name(cls, name):
        """Get role by name"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_or_create(cls, name, description=None):
        """Get existing role or create new one if it doesn't exist"""
        role = cls.query.filter_by(name=name).first()
        if not role:
            role = cls(name=name, description=description)
            db.session.add(role)
            db.session.commit()
        return role
    
    def __repr__(self):
        return f'<Role {self.id}: {self.name}>'

