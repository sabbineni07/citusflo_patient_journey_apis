from app import db
from datetime import datetime
import json

class PatientForm(db.Model):
    """Model for storing patient forms with versioning/history"""
    __tablename__ = 'patient_forms'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, nullable=False, index=True)  # Unique identifier for the form instance (allows multiple versions)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    form_type = db.Column(db.String(100), nullable=False, index=True)  # e.g., 'intake', 'assessment', 'discharge'
    form_data = db.Column(db.JSON, nullable=False)  # The actual form data as JSON
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship with patient
    patient = db.relationship('Patient', backref=db.backref('form_history', cascade='all, delete-orphan'), lazy=True)
    
    # Relationship with user who created the form
    creator = db.relationship('User', foreign_keys=[created_by], lazy=True)
    
    def to_dict(self):
        """Convert patient form to dictionary"""
        return {
            'id': self.id,
            'formId': self.form_id,
            'patientId': self.patient_id,
            'formType': self.form_type,
            'formData': self.form_data,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<PatientForm {self.id}: Patient {self.patient_id} - {self.form_type}>'

