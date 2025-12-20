from app import db
from app.models.patient import Patient
from app.models.patient_form import PatientForm
from app.models.facility import Facility
from app.models.user import User
from app.models.hospital import Hospital
from datetime import datetime
from sqlalchemy import or_, func, desc
import uuid
import re

class PatientService:
    """Service class for patient operations"""
    
    def _parse_datetime(self, datetime_str):
        """Parse datetime string to datetime object, handling various formats"""
        if not datetime_str:
            return None
        try:
            # Handle ISO format with timezone (Z or +00:00)
            if isinstance(datetime_str, str):
                # Replace Z with +00:00 for timezone handling
                datetime_str = datetime_str.replace('Z', '+00:00')
                return datetime.fromisoformat(datetime_str)
            elif isinstance(datetime_str, datetime):
                return datetime_str
            else:
                return None
        except (ValueError, AttributeError, TypeError):
            return None
    
    def _parse_date(self, date_str):
        """Parse date string to date object, handling various formats"""
        if not date_str:
            return None
        try:
            if isinstance(date_str, str):
                # Try ISO format (YYYY-MM-DD)
                if 'T' in date_str:
                    date_str = date_str.split('T')[0]
                if ' ' in date_str:
                    date_str = date_str.split(' ')[0]
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            elif isinstance(date_str, datetime):
                return date_str.date()
            else:
                return None
        except (ValueError, AttributeError, TypeError):
            return None
    
    def _determine_hospital_id(self, user, patient_data):
        """Determine hospital_id based on user context and patient data
        
        Args:
            user: User object who is creating the patient
            patient_data: Patient data dictionary
        
        Returns:
            hospital_id (int or None): Hospital ID to link facility to
        """
        # Priority 1: hospital_id provided directly in patient_data
        if 'hospital_id' in patient_data and patient_data.get('hospital_id'):
            try:
                hospital_id = int(patient_data['hospital_id'])
                # Verify hospital exists
                hospital = Hospital.query.get(hospital_id)
                if hospital:
                    return hospital_id
            except (ValueError, TypeError):
                pass
        
        # Priority 2: hospitalName provided in patient_data - look up hospital by name
        if 'hospitalName' in patient_data and patient_data.get('hospitalName'):
            hospital_name = patient_data['hospitalName'].strip()
            if hospital_name:
                hospital = Hospital.query.filter_by(name=hospital_name).first()
                if hospital:
                    return hospital.id
        
        # Priority 3: Get hospital_id from user's facility
        if user.facility_id and user.facility:
            if user.facility.hospital_id:
                return user.facility.hospital_id
        
        # Priority 4: Get hospital_id from user's home_health's hospitals
        if user.home_health_id and user.home_health:
            hospitals = user.home_health.hospitals
            if hospitals:
                # Use the first hospital if multiple are linked
                return hospitals[0].id
        
        # No hospital found
        return None
    
    def create_patient(self, patient_data, created_by):
        """Create a new patient
        
        Args:
            patient_data: Dictionary containing patient data
            created_by: User ID (int) of the user creating the patient
        """
        # Get user object to determine hospital context
        if isinstance(created_by, int):
            user_id = created_by
            user = User.query.get(created_by)
        else:
            user = created_by
            user_id = user.id if user else None
        
        if not user:
            raise ValueError(f"User with ID {created_by} not found")
        
        # Determine hospital_id from user context
        hospital_id = self._determine_hospital_id(user, patient_data)
        
        # Handle facility creation/assignment using facility_name
        facility_name = patient_data.get('facilityName')
        facility_id = None
        
        if facility_name:
            # Get or create facility using facility_name, with hospital_id if available
            facility = Facility.get_or_create(
                name=facility_name,
                address=patient_data.get('facilityAddress'),
                phone=patient_data.get('facilityPhone'),
                hospital_id=hospital_id
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
            
        # Handle forms - will be saved to patient_forms table
        forms_data = patient_data.get('forms', [])
        if not isinstance(forms_data, list):
            forms_data = []
        
        # Handle home_health_id if provided
        home_health_id = patient_data.get('home_health_id')
        if home_health_id:
            try:
                home_health_id = int(home_health_id)
            except (ValueError, TypeError):
                home_health_id = None
        
        patient = Patient(
            case_manager_name=patient_data['caseManagerName'],
            phone_number=patient_data['phoneNumber'],
            facility_name=facility_name,
            facility_id=facility_id,
            home_health_id=home_health_id,
            patient_name=patient_data['patientName'],
            date=datetime.strptime(patient_data['date'], '%Y-%m-%d').date(),
            date_of_birth=self._parse_date(patient_data.get('dateOfBirth')),
            referral_received=patient_data.get('referralReceived', False),
            insurance_verification=patient_data.get('insuranceVerification', False),
            family_and_patient_aware=patient_data.get('familyAndPatientAware', False),
            in_person_visit=patient_data.get('inPersonVisit', False),
            discharged_from_facility=patient_data.get('dischargedFromFacility', False),
            admitted=patient_data.get('admitted', False),
            care_follow_up=patient_data.get('careFollowUp', False),
            active=patient_data.get('active', True),
            admitted_datetime=self._parse_datetime(patient_data.get('admittedDatetime')),
            notes=patient_data.get('notes'),
            form_content=patient_data.get('formContent'),
            forms=forms_data,  # Store forms as JSON
            created_by=user_id
        )
        
        # Save patient to database
        db.session.add(patient)
        db.session.flush()  # Flush to get patient.id
        
        # Save forms to patient_forms table
        self._save_forms_to_table(patient.id, forms_data, user_id)
        
        db.session.commit()
        
        return patient
    
    def _save_forms_to_table(self, patient_id, forms_data, created_by=None):
        """Save forms to patient_forms table (append, not replace)
        
        Args:
            patient_id: Patient ID
            forms_data: List of form objects. Each can be:
                - {"formId": 1, "formType": "intake", "formData": {...}}
                - {"id": 1, "formType": "intake", "formData": {...}}
                - {"formType": "intake", "formData": {...}} (formId will be generated)
            created_by: User ID who created the forms
            
        Behavior:
        - Always creates new entries for all forms sent (versioning/history)
        - If formId is provided, uses it (for updates to existing forms)
        - If formId is not provided, generates a new unique form_id
        - If multiple forms have the same form_type in the request, only the last one is saved
        - When returning forms via patient model, get_latest_forms() returns most recent per form_id
        """
        from app.models.patient_form import PatientForm
        from sqlalchemy import func
        
        # Track forms by type to ensure we only save one form per type in this request
        # This prevents duplicates when frontend sends multiple forms with same form_type
        forms_by_type = {}
        
        for form_item in forms_data:
            if not isinstance(form_item, dict):
                continue
            
            # Extract form_id - can be formId, id, or form_id
            form_id = form_item.get('formId') or form_item.get('form_id') or form_item.get('id')
            
            # Extract form_type - required field (try multiple field names)
            form_type = form_item.get('formType') or form_item.get('form_type') or form_item.get('type') or 'unknown'
            
            # Extract form_data - can be nested or the whole item
            # Priority: formData > form_data > data > entire form_item (excluding metadata)
            if 'formData' in form_item:
                form_data = form_item['formData']
            elif 'form_data' in form_item:
                form_data = form_item['form_data']
            elif 'data' in form_item:
                form_data = form_item['data']
            else:
                # Use entire form_item but remove metadata fields
                form_data = {k: v for k, v in form_item.items() 
                           if k not in ['formType', 'form_type', 'type', 'id', 'formId', 'form_id', 'createdAt', 'created_at', 'createdBy', 'created_by']}
            
            # Ensure form_data is a dict (if it's None or empty, use empty dict)
            if not isinstance(form_data, dict):
                form_data = {'value': form_data} if form_data is not None else {}
            
            # Convert form_id to integer if possible, otherwise set to None (will generate new one)
            # Handle cases where frontend sends string IDs like 'form-1766197035107'
            # IMPORTANT: PostgreSQL INTEGER range is -2,147,483,648 to 2,147,483,647
            # If extracted value exceeds this range, generate a new form_id instead
            INTEGER_MAX = 2147483647  # PostgreSQL INTEGER maximum value
            
            form_id_int = None
            if form_id is not None:
                try:
                    # Try direct conversion
                    form_id_int = int(form_id)
                    # Validate it's within INTEGER range
                    if form_id_int > INTEGER_MAX or form_id_int < -2147483648:
                        form_id_int = None  # Too large, will generate new one
                except (ValueError, TypeError):
                    # If form_id is a string that can't be converted (e.g., 'form-1766197035107'),
                    # try to extract numeric part if it follows a pattern like 'form-123456'
                    if isinstance(form_id, str):
                        # Try to extract number after last dash or underscore
                        match = re.search(r'(\d+)$', form_id)
                        if match:
                            try:
                                extracted_value = int(match.group(1))
                                # Validate it's within INTEGER range (frontend timestamps often exceed this)
                                if extracted_value <= INTEGER_MAX and extracted_value >= -2147483648:
                                    form_id_int = extracted_value
                                else:
                                    # Timestamp-based IDs (like 1766198419087) are too large for INTEGER
                                    # Generate new form_id instead
                                    form_id_int = None
                            except (ValueError, TypeError):
                                form_id_int = None
                        else:
                            form_id_int = None
                    else:
                        form_id_int = None
            
            # Store form by type (overwrite if same type appears multiple times - keep latest)
            forms_by_type[str(form_type)] = {
                'form_id': form_id_int,
                'form_type': str(form_type),
                'form_data': form_data
            }
        
        # Always create new entries for all forms (versioning/history)
        for form_type, form_info in forms_by_type.items():
            form_id = form_info['form_id']
            
            # If form_id not provided, generate a new unique one
            if form_id is None:
                # Get the max form_id for this patient and increment
                max_form_id = db.session.query(func.max(PatientForm.form_id)).filter_by(
                    patient_id=patient_id
                ).scalar()
                form_id = (max_form_id or 0) + 1
            
            patient_form = PatientForm(
                form_id=form_id,
                patient_id=patient_id,
                form_type=form_info['form_type'],
                form_data=form_info['form_data'],
                created_by=created_by
            )
            db.session.add(patient_form)
    
    def _get_latest_forms_per_type(self, patient_id):
        """Get the most recent form per form_type for a patient (no duplicates)"""
        from app.models.patient import Patient
        patient = Patient.query.get(patient_id)
        if patient:
            return patient.get_latest_forms()
        return []
    
    def update_patient(self, patient, patient_data, current_user_id=None):
        """Update an existing patient
        
        Args:
            patient: Patient object to update
            patient_data: Dictionary containing patient data to update
            current_user_id: User ID of the current user making the update (for form tracking)
        """
        # Get user object if available for hospital context
        user = None
        if patient.created_by:
            user = User.query.get(patient.created_by)
        
        # Determine hospital_id for facility creation/update
        hospital_id = None
        if user:
            hospital_id = self._determine_hospital_id(user, patient_data)
        
        # Handle facility update using facility_name
        if 'facilityName' in patient_data:
            facility_name = patient_data['facilityName']
            if facility_name:
                # Get or create facility using facility_name, with hospital_id if available
                facility = Facility.get_or_create(
                    name=facility_name,
                    address=patient_data.get('facilityAddress'),
                    phone=patient_data.get('facilityPhone'),
                    hospital_id=hospital_id
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
            if key == 'date':
                # Handle date field (requires parsing)
                if value:
                    try:
                        # Handle ISO format dates (may include time)
                        if isinstance(value, str):
                            # Extract just the date part if datetime string provided
                            date_str = value.split('T')[0] if 'T' in value else value.split(' ')[0]
                            patient.date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        # If parsing fails, skip the update
                        pass
            elif key == 'dateOfBirth':
                # Handle date_of_birth field (requires parsing)
                patient.date_of_birth = self._parse_date(value)
            elif key in field_mapping:
                db_field = field_mapping[key]
                if hasattr(patient, db_field) and db_field not in ['id', 'created_at', 'created_by', 'facility_name', 'facility_id']:
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
            elif key == 'home_health_id':
                # Handle home_health_id update
                if value and str(value).strip():
                    try:
                        patient.home_health_id = int(value)
                    except (ValueError, TypeError):
                        patient.home_health_id = None
                else:
                    patient.home_health_id = None
            elif key == 'forms':
                # Handle forms update
                # If forms array is provided (even if empty), it represents the desired state
                # Forms not in the array should be deleted
                if isinstance(value, list):
                    # Use the current_user_id passed to the method (from the route)
                    # This ensures we capture the session user who is making the update
                    user_id_for_forms = current_user_id if current_user_id else None
                    
                    # Get current form_ids that should be kept
                    form_ids_to_keep = set()
                    if len(value) > 0:
                        # Extract form_ids from the forms array that should be kept
                        for form_item in value:
                            if isinstance(form_item, dict):
                                form_id = form_item.get('formId') or form_item.get('form_id') or form_item.get('id')
                                if form_id is not None:
                                    try:
                                        # Handle string IDs like 'form-1766197035107'
                                        if isinstance(form_id, str):
                                            match = re.search(r'(\d+)$', form_id)
                                            if match:
                                                form_id_int = int(match.group(1))
                                                # Only keep if within INTEGER range
                                                if form_id_int <= 2147483647 and form_id_int >= -2147483648:
                                                    form_ids_to_keep.add(form_id_int)
                                            # If it's a simple integer string, try direct conversion
                                            elif form_id.isdigit():
                                                form_id_int = int(form_id)
                                                if form_id_int <= 2147483647 and form_id_int >= -2147483648:
                                                    form_ids_to_keep.add(form_id_int)
                                        else:
                                            form_id_int = int(form_id)
                                            if form_id_int <= 2147483647 and form_id_int >= -2147483648:
                                                form_ids_to_keep.add(form_id_int)
                                    except (ValueError, TypeError):
                                        pass  # Skip invalid form_ids
                    
                    # Delete forms that are not in the keep list
                    if form_ids_to_keep:
                        # Delete forms with form_ids not in the keep list
                        PatientForm.query.filter(
                            PatientForm.patient_id == patient.id,
                            ~PatientForm.form_id.in_(form_ids_to_keep)
                        ).delete(synchronize_session=False)
                    else:
                        # If forms array is empty or no valid form_ids, delete all forms for this patient
                        PatientForm.query.filter_by(patient_id=patient.id).delete()
                    
                    # Save new/updated forms (this will create new versions for existing form_ids)
                    if len(value) > 0:
                        self._save_forms_to_table(patient.id, value, created_by=user_id_for_forms)
            elif key == 'active':
                # Handle active field
                if value is not None:
                    patient.active = bool(value)
            elif key == 'admitted':
                # Handle admitted field (boolean, no camelCase conversion needed)
                if value is not None:
                    patient.admitted = bool(value)
            elif key == 'admittedDatetime':
                # Handle admitted_datetime field
                patient.admitted_datetime = self._parse_datetime(value)
            elif key == 'notes':
                # Handle notes field
                patient.notes = value if value else None
        
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
                or_(
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
