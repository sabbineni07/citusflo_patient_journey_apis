from app import db
from datetime import datetime

class Facility(db.Model):
    __tablename__ = 'facilities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with patients
    patients = db.relationship('Patient', backref='facility_ref', lazy=True)
    
    # Relationship with hospital (backref defined in Hospital model)
    
    def to_dict(self):
        """Convert facility to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'hospital_id': self.hospital_id,
            'hospital_name': self.hospital.name if self.hospital else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def get_or_create(cls, name, address=None, phone=None, hospital_id=None):
        """Get existing facility or create new one if it doesn't exist
        
        Args:
            name: Facility name
            address: Facility address (optional)
            phone: Facility phone (optional)
            hospital_id: Hospital ID to link facility to (optional)
        
        Returns:
            Facility object
        """
        facility = cls.query.filter_by(name=name).first()
        if not facility:
            facility = cls(name=name, address=address, phone=phone, hospital_id=hospital_id)
            db.session.add(facility)
            db.session.commit()
        elif facility.hospital_id is None and hospital_id is not None:
            # Update existing facility with hospital_id if it doesn't have one
            facility.hospital_id = hospital_id
            db.session.commit()
        return facility
    
    def __repr__(self):
        return f'<Facility {self.id}: {self.name}>'
