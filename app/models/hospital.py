from app import db
from datetime import datetime

# Junction table for many-to-many relationship between HomeHealth and Hospital
home_health_hospitals = db.Table(
    'home_health_hospitals',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('home_health_id', db.Integer, db.ForeignKey('home_health.id'), nullable=False),
    db.Column('hospital_id', db.Integer, db.ForeignKey('hospitals.id'), nullable=False),
    db.Column('created_at', db.DateTime, default=datetime.utcnow, nullable=False),
    db.UniqueConstraint('home_health_id', 'hospital_id', name='uq_home_health_hospital')
)

class Hospital(db.Model):
    """Model for storing hospital information"""
    __tablename__ = 'hospitals'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with facilities (one-to-many)
    facilities = db.relationship('Facility', backref='hospital', lazy=True)
    
    # Relationship with home_health (many-to-many via junction table)
    home_health_agencies = db.relationship(
        'HomeHealth',
        secondary=home_health_hospitals,
        back_populates='hospitals',
        lazy=True
    )
    
    def to_dict(self):
        """Convert hospital to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Hospital {self.id}: {self.name}>'

