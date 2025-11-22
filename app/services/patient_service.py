from app import db
from app.models.patient import Patient
from app.models.facility import Facility
from datetime import datetime
import uuid

class PatientService:
    """Service class for patient operations"""
    
    def create_patient(self, patient_data, created_by):
        """Create a new patient"""
        # Handle facility creation/assignment using facility_name
        facility_name = patient_data.get('facilityName')
        facility_id = None
        
        if facility_name:
            # Get or create facility using facility_name
            facility = Facility.get_or_create(
                name=facility_name,
                address=patient_data.get('facilityAddress'),
                phone=patient_data.get('facilityPhone')
            )
            facility_id = facility.id
        else:
            # Fallback: handle direct facility_id if provided
            facility_id = patient_data.get('facility_id')
            if facility_id and str(facility_id).strip():
                try:
                    facility_id = int(facility_id)
                except (ValueError, TypeError):
                    facility_id = None
            
        # Handle forms - ensure it's a list
        forms_data = patient_data.get('forms', [])
        if not isinstance(forms_data, list):
            forms_data = []
        
        patient = Patient(
            case_manager_name=patient_data['caseManagerName'],
            phone_number=patient_data['phoneNumber'],
            facility_name=facility_name,
            facility_id=facility_id,
            patient_name=patient_data['patientName'],
            date=datetime.strptime(patient_data['date'], '%Y-%m-%d').date(),
            referral_received=patient_data.get('referralReceived', False),
            insurance_verification=patient_data.get('insuranceVerification', False),
            family_and_patient_aware=patient_data.get('familyAndPatientAware', False),
            in_person_visit=patient_data.get('inPersonVisit', False),
            discharged_from_facility=patient_data.get('dischargedFromFacility', False),
            admitted=patient_data.get('admitted', False),
            care_follow_up=patient_data.get('careFollowUp', False),
            form_content=patient_data.get('formContent'),
            forms=forms_data,  # Store forms as JSON
            created_by=created_by
        )
        
        # Save to database
        db.session.add(patient)
        db.session.commit()
        
        return patient
    
    def update_patient(self, patient, patient_data):
        """Update an existing patient"""
        # Handle facility update using facility_name
        if 'facilityName' in patient_data:
            facility_name = patient_data['facilityName']
            if facility_name:
                # Get or create facility using facility_name
                facility = Facility.get_or_create(
                    name=facility_name,
                    address=patient_data.get('facilityAddress'),
                    phone=patient_data.get('facilityPhone')
                )
                patient.facility_id = facility.id
                patient.facility_name = facility_name
            else:
                patient.facility_id = None
                patient.facility_name = None
        
        # Map camelCase to snake_case for database fields
        field_mapping = {
            'caseManagerName': 'case_manager_name',
            'phoneNumber': 'phone_number',
            'patientName': 'patient_name',
            'referralReceived': 'referral_received',
            'insuranceVerification': 'insurance_verification',
            'familyAndPatientAware': 'family_and_patient_aware',
            'inPersonVisit': 'in_person_visit',
            'dischargedFromFacility': 'discharged_from_facility',
            'careFollowUp': 'care_follow_up',
            'formContent': 'form_content'
        }
        
        # Update other fields
        for key, value in patient_data.items():
            if key in field_mapping:
                db_field = field_mapping[key]
                if hasattr(patient, db_field) and db_field not in ['id', 'created_at', 'created_by', 'facility_name', 'facility_id']:
                    if key == 'date' and value:
                        patient.date = datetime.strptime(value, '%Y-%m-%d').date()
                    else:
                        setattr(patient, db_field, value)
            elif key == 'facility_id' and 'facilityName' not in patient_data:
                # Handle direct facility_id update only if facilityName is not provided
                if value and str(value).strip():
                    try:
                        patient.facility_id = int(value)
                    except (ValueError, TypeError):
                        patient.facility_id = None
                else:
                    patient.facility_id = None
            elif key == 'forms':
                # Handle forms update
                if isinstance(value, list):
                    patient.forms = value
                else:
                    patient.forms = []
        
        patient.updated_at = datetime.utcnow()
        db.session.commit()
        
        return patient
    
    def get_patients(self, page=1, per_page=10, search=''):
        """Get patients with filtering and pagination"""
        query = Patient.query
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Patient.patient_name.ilike(search_term),
                    Patient.case_manager_name.ilike(search_term),
                    Patient.facility_name.ilike(search_term),
                    Patient.phone_number.ilike(search_term)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        patients = query.order_by(Patient.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        ).items
        
        return patients, total
    
    def get_patient_by_id(self, patient_id):
        """Get patient by ID"""
        return Patient.query.get(patient_id)
    
    def delete_patient(self, patient):
        """Delete a patient"""
        db.session.delete(patient)
        db.session.commit()
        
        return patient
