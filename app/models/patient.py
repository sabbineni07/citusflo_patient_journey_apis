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
    date_of_birth = db.Column(db.Date, nullable=True)
    referral_received = db.Column(db.Boolean, default=False)
    insurance_verification = db.Column(db.Boolean, default=False)
    contact_made = db.Column(db.Boolean, default=False)  # Made contact with patient/family
    clinical_liaison_visit = db.Column(db.Boolean, default=False)  # Clinical liaison visit
    discharged_from_facility = db.Column(db.DateTime, nullable=True)  # Discharged from facility datetime
    admitted_datetime = db.Column(db.DateTime, nullable=True)  # Admitted datetime
    soc_1week_followup = db.Column(db.Boolean, default=False)  # SOC 1 week follow up
    patient_accepted = db.Column(db.Boolean, nullable=True)  # Patient Accepted / Patient declined
    active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    form_content = db.Column(db.Text)
    forms = db.Column(db.JSON, default=list)  # JSON field to store array of forms
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with facility
    facility = db.relationship('Facility', lazy=True)
    
    # Relationship with home health agency
    home_health = db.relationship('HomeHealth', lazy=True)
    
    def get_latest_forms(self):
        """Get the most recent form per form_id for this patient (no duplicates)
        
        Returns all unique form_ids ordered by created_at DESC, with only the most recent
        entry for each form_id. This allows tracking form history while returning only
        the latest version of each form.
        """
        from sqlalchemy import func
        from app.models.patient_form import PatientForm
        
        # Subquery to get the max created_at per form_id for this patient
        subquery = db.session.query(
            PatientForm.form_id,
            func.max(PatientForm.created_at).label('max_created_at')
        ).filter(
            PatientForm.patient_id == self.id
        ).group_by(
            PatientForm.form_id
        ).subquery()
        
        # Query to get the actual form records matching the latest timestamps
        # Order by created_at DESC to return newest forms first
        latest_forms = db.session.query(PatientForm).join(
            subquery,
            (PatientForm.form_id == subquery.c.form_id) &
            (PatientForm.created_at == subquery.c.max_created_at) &
            (PatientForm.patient_id == self.id)
        ).order_by(PatientForm.created_at.desc()).all()
        
        return latest_forms
    
    def to_dict(self):
        """Convert patient to dictionary"""
        # Get latest forms per form_type from patient_forms table (no duplicates)
        latest_forms = self.get_latest_forms()
        
        # Convert to list of dictionaries, preserving form_type
        forms_data = []
        for form in latest_forms:
            # Get creator full name if available
            created_by_name = None
            if form.creator:
                # Get full name (first_name + last_name)
                if form.creator.first_name and form.creator.last_name:
                    created_by_name = f"{form.creator.first_name} {form.creator.last_name}".strip()
                elif form.creator.first_name:
                    created_by_name = form.creator.first_name
                elif form.creator.last_name:
                    created_by_name = form.creator.last_name
                else:
                    created_by_name = form.creator.username  # Fallback to username if no name
            elif form.created_by:
                # Fallback: try to get user if relationship not loaded
                from app.models.user import User
                creator = User.query.get(form.created_by)
                if creator:
                    if creator.first_name and creator.last_name:
                        created_by_name = f"{creator.first_name} {creator.last_name}".strip()
                    elif creator.first_name:
                        created_by_name = creator.first_name
                    elif creator.last_name:
                        created_by_name = creator.last_name
                    else:
                        created_by_name = creator.username  # Fallback to username if no name
            
            forms_data.append({
                'id': form.id,
                'formId': form.form_id,
                'formType': form.form_type,
                'formData': form.form_data,
                'createdBy': created_by_name,  # Return username instead of ID
                'createdAt': form.created_at.isoformat() if form.created_at else None
            })
        
        # Also keep legacy forms field for backward compatibility (if exists)
        legacy_forms_data = self.forms if self.forms is not None else []
        if isinstance(legacy_forms_data, str):
            try:
                legacy_forms_data = json.loads(legacy_forms_data)
            except (json.JSONDecodeError, TypeError):
                legacy_forms_data = []
        if not isinstance(legacy_forms_data, list):
            legacy_forms_data = []
        
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
            'dateOfBirth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'referralReceived': self.referral_received,
            'insuranceVerification': self.insurance_verification,
            'contactMade': self.contact_made,
            'clinicalLiaisonVisit': self.clinical_liaison_visit,
            'dischargedFromFacility': self.discharged_from_facility.isoformat() if self.discharged_from_facility else None,
            'admittedDatetime': self.admitted_datetime.isoformat() if self.admitted_datetime else None,
            'soc1WeekFollowup': self.soc_1week_followup,
            'patientAccepted': self.patient_accepted,
            'active': self.active,
            'notes': self.notes,
            'formContent': self.form_content,
            'forms': forms_data,  # Include forms array
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Patient {self.id}: {self.patient_name}>'
