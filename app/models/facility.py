from app import db
from datetime import datetime

class Facility(db.Model):
    __tablename__ = 'facilities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with patients
    patients = db.relationship('Patient', backref='facility_ref', lazy=True)
    
    def to_dict(self):
        """Convert facility to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def get_or_create(cls, name, address=None, phone=None):
        """Get existing facility or create new one if it doesn't exist"""
        facility = cls.query.filter_by(name=name).first()
        if not facility:
            facility = cls(name=name, address=address, phone=phone)
            db.session.add(facility)
            db.session.commit()
        return facility
    
    def __repr__(self):
        return f'<Facility {self.id}: {self.name}>'
