from app import db
from datetime import datetime

class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    case_manager_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    facility_name = db.Column(db.String(100), nullable=False)
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
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert patient to dictionary"""
        return {
            'id': self.id,
            'caseManagerName': self.case_manager_name,
            'phoneNumber': self.phone_number,
            'facilityName': self.facility_name,
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
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Patient {self.id}: {self.patient_name}>'
