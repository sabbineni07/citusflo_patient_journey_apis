from app import db
from datetime import datetime
import json

class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    case_manager_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    facility_name = db.Column(db.String(100), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=True)
    home_health_id = db.Column(db.Integer, db.ForeignKey('home_health.id'), nullable=True)
    patient_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    referral_received = db.Column(db.Boolean, default=False)
    insurance_verification = db.Column(db.Boolean, default=False)
    family_and_patient_aware = db.Column(db.Boolean, default=False)
    in_person_visit = db.Column(db.Boolean, default=False)
    discharged_from_facility = db.Column(db.Boolean, default=False)
    admitted = db.Column(db.Boolean, default=False)
    care_follow_up = db.Column(db.Boolean, default=False)
    form_content = db.Column(db.Text)
    forms = db.Column(db.JSON, default=list)  # JSON field to store array of forms
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with facility
    facility = db.relationship('Facility', lazy=True)
    
    # Relationship with home health agency
    home_health = db.relationship('HomeHealth', lazy=True)
    
    def to_dict(self):
        """Convert patient to dictionary"""
        # Handle forms - ensure it's always a list
        forms_data = self.forms if self.forms is not None else []
        if isinstance(forms_data, str):
            try:
                forms_data = json.loads(forms_data)
            except (json.JSONDecodeError, TypeError):
                forms_data = []
        if not isinstance(forms_data, list):
            forms_data = []
        
        return {
            'id': str(self.id),
            'caseManagerName': self.case_manager_name,
            'phoneNumber': self.phone_number,
            'facilityName': self.facility_name,
            'facility_id': self.facility_id,
            'facility_name_from_relation': self.facility.name if self.facility else None,
            'home_health_id': self.home_health_id,
            'home_health_name': self.home_health.name if self.home_health else None,
            'patientName': self.patient_name,
            'date': self.date.isoformat() if self.date else None,
            'referralReceived': self.referral_received,
            'insuranceVerification': self.insurance_verification,
            'familyAndPatientAware': self.family_and_patient_aware,
            'inPersonVisit': self.in_person_visit,
            'dischargedFromFacility': self.discharged_from_facility,
            'admitted': self.admitted,
            'careFollowUp': self.care_follow_up,
            'formContent': self.form_content,
            'forms': forms_data,  # Include forms array
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Patient {self.id}: {self.patient_name}>'
