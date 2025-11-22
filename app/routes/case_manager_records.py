from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.patient import Patient
from app.services.patient_service import PatientService
from app.utils.validators import validate_patient_data
from datetime import datetime, timedelta
import json

case_manager_records_bp = Blueprint('case_manager_records', __name__)
patient_service = PatientService()

@case_manager_records_bp.route('/', methods=['GET'])
@jwt_required()
def get_case_manager_records():
    """Get case manager records with filtering and pagination"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        facility_id = request.args.get('facility_id')
        
        # Build query
        query = Patient.query
        
        # Filter by facility if specified (admin can see all, users see only their facility)
        if user.role_name != 'admin' and user.facility_id:
            query = query.filter(Patient.facility_id == user.facility_id)
        elif facility_id:
            query = query.filter(Patient.facility_id == int(facility_id))
        
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
        
        # Apply date filters
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00')).date()
                query = query.filter(Patient.date >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format. Use ISO format.'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00')).date()
                query = query.filter(Patient.date <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format. Use ISO format.'}), 400
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        patients = query.order_by(Patient.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        ).items

        print(patients)
        
        # Transform to case manager records format
        records = []
        for patient in patients:
            # Handle forms - ensure it's always a list
            forms_data = patient.forms if patient.forms is not None else []
            if isinstance(forms_data, str):
                try:
                    forms_data = json.loads(forms_data)
                except (json.JSONDecodeError, TypeError):
                    forms_data = []
            if not isinstance(forms_data, list):
                forms_data = []
            
            record = {
                'id': str(patient.id),
                'caseManagerName': patient.case_manager_name,
                'phoneNumber': patient.phone_number,
                'facilityName': patient.facility_name,
                'facility_id': str(patient.facility_id) if patient.facility_id else None,
                'facility': patient.facility.to_dict() if patient.facility else None,
                'patientName': patient.patient_name,
                'date': patient.date.isoformat() if patient.date else None,
                'referralReceived': patient.referral_received,
                'insuranceVerification': patient.insurance_verification,
                'familyAndPatientAware': patient.family_and_patient_aware,
                'inPersonVisit': patient.in_person_visit,
                'dischargedFromFacility': patient.discharged_from_facility,
                'admitted': patient.admitted,
                'careFollowUp': patient.care_follow_up,
                'formContent': patient.form_content,
                'forms': forms_data,  # Include forms array
                'created_at': patient.created_at.isoformat(),
                'updated_at': patient.updated_at.isoformat()
            }
            records.append(record)
        
        return jsonify({
            'records': records,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@case_manager_records_bp.route('/<int:record_id>', methods=['GET'])
@jwt_required()
def get_case_manager_record(record_id):
    """Get a specific case manager record by ID"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        patient = Patient.query.get(record_id)
        
        if not patient:
            return jsonify({'error': 'Record not found'}), 404
        
        # Handle forms - ensure it's always a list
        forms_data = patient.forms if patient.forms is not None else []
        if isinstance(forms_data, str):
            try:
                forms_data = json.loads(forms_data)
            except (json.JSONDecodeError, TypeError):
                forms_data = []
        if not isinstance(forms_data, list):
            forms_data = []
        
        record = {
            'id': str(patient.id),
            'caseManagerName': patient.case_manager_name,
            'phoneNumber': patient.phone_number,
            'facilityName': patient.facility_name,
            'facility_id': patient.facility_id,
            'patientName': patient.patient_name,
            'date': patient.date.isoformat() if patient.date else None,
            'referralReceived': patient.referral_received,
            'insuranceVerification': patient.insurance_verification,
            'familyAndPatientAware': patient.family_and_patient_aware,
            'inPersonVisit': patient.in_person_visit,
            'dischargedFromFacility': patient.discharged_from_facility,
            'admitted': patient.admitted,
            'careFollowUp': patient.care_follow_up,
            'formContent': patient.form_content,
            'forms': forms_data,  # Include forms array
            'created_at': patient.created_at.isoformat(),
            'updated_at': patient.updated_at.isoformat()
        }
        
        return jsonify({
            'record': record
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@case_manager_records_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_case_manager_stats():
    """Get case manager statistics"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get date filters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        facility_id = request.args.get('facility_id')
        
        # Build base query
        query = Patient.query
        
        # Filter by facility if specified (admin can see all, users see only their facility)
        if user.role_name != 'admin' and user.facility_id:
            query = query.filter(Patient.facility_id == user.facility_id)
        elif facility_id:
            query = query.filter(Patient.facility_id == int(facility_id))
        
        # Apply date filters
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00')).date()
                query = query.filter(Patient.date >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format. Use ISO format.'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00')).date()
                query = query.filter(Patient.date <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format. Use ISO format.'}), 400
        
        # Calculate statistics
        total_records = query.count()
        referral_received = query.filter(Patient.referral_received == True).count()
        insurance_verified = query.filter(Patient.insurance_verification == True).count()
        family_aware = query.filter(Patient.family_and_patient_aware == True).count()
        in_person_visits = query.filter(Patient.in_person_visit == True).count()
        discharged = query.filter(Patient.discharged_from_facility == True).count()
        admitted = query.filter(Patient.admitted == True).count()
        care_follow_up = query.filter(Patient.care_follow_up == True).count()
        
        stats = {
            'total_records': total_records,
            'referral_received': referral_received,
            'insurance_verified': insurance_verified,
            'family_aware': family_aware,
            'in_person_visits': in_person_visits,
            'discharged': discharged,
            'admitted': admitted,
            'care_follow_up': care_follow_up,
            'referral_rate': round((referral_received / total_records * 100) if total_records > 0 else 0, 2),
            'insurance_verification_rate': round((insurance_verified / total_records * 100) if total_records > 0 else 0, 2),
            'admission_rate': round((admitted / total_records * 100) if total_records > 0 else 0, 2)
        }
        
        return jsonify({
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@case_manager_records_bp.route('/', methods=['POST'])
@jwt_required()
def create_case_manager_record():
    """Create a new case manager record"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Validate input data
        validation_errors = validate_patient_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Create new patient record
        patient = patient_service.create_patient(data, int(user_id))
        
        # Handle forms if provided
        if 'forms' in data and data['forms']:
            if isinstance(data['forms'], list):
                patient.forms = data['forms']
            else:
                patient.forms = []
        else:
            patient.forms = []
        
        db.session.commit()
        
        # Get forms data for response
        forms_data = patient.forms if patient.forms is not None else []
        if isinstance(forms_data, str):
            try:
                forms_data = json.loads(forms_data)
            except (json.JSONDecodeError, TypeError):
                forms_data = []
        if not isinstance(forms_data, list):
            forms_data = []
        
        record = {
            'id': str(patient.id),
            'caseManagerName': patient.case_manager_name,
            'phoneNumber': patient.phone_number,
            'facilityName': patient.facility_name,
            'facility_id': str(patient.facility_id) if patient.facility_id else None,
            'patientName': patient.patient_name,
            'date': patient.date.isoformat() if patient.date else None,
            'referralReceived': patient.referral_received,
            'insuranceVerification': patient.insurance_verification,
            'familyAndPatientAware': patient.family_and_patient_aware,
            'inPersonVisit': patient.in_person_visit,
            'dischargedFromFacility': patient.discharged_from_facility,
            'admitted': patient.admitted,
            'careFollowUp': patient.care_follow_up,
            'formContent': patient.form_content,
            'forms': forms_data,
            'created_at': patient.created_at.isoformat(),
            'updated_at': patient.updated_at.isoformat()
        }
        
        return jsonify({
            'message': 'Case manager record created successfully',
            'patient': record
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@case_manager_records_bp.route('/<int:record_id>', methods=['PUT'])
@jwt_required()
def update_case_manager_record(record_id):
    """Update an existing case manager record"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        patient = Patient.query.get(record_id)
        
        if not patient:
            return jsonify({'error': 'Record not found'}), 404
        
        data = request.get_json()
        
        # Validate input data
        validation_errors = validate_patient_data(data, is_update=True)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Update patient record
        updated_patient = patient_service.update_patient(patient, data)
        
        # Handle forms if provided
        if 'forms' in data:
            if isinstance(data['forms'], list):
                updated_patient.forms = data['forms']
            else:
                updated_patient.forms = []
        
        db.session.commit()
        
        # Get forms data for response
        forms_data = updated_patient.forms if updated_patient.forms is not None else []
        if isinstance(forms_data, str):
            try:
                forms_data = json.loads(forms_data)
            except (json.JSONDecodeError, TypeError):
                forms_data = []
        if not isinstance(forms_data, list):
            forms_data = []
        
        record = {
            'id': str(updated_patient.id),
            'caseManagerName': updated_patient.case_manager_name,
            'phoneNumber': updated_patient.phone_number,
            'facilityName': updated_patient.facility_name,
            'facility_id': str(updated_patient.facility_id) if updated_patient.facility_id else None,
            'patientName': updated_patient.patient_name,
            'date': updated_patient.date.isoformat() if updated_patient.date else None,
            'referralReceived': updated_patient.referral_received,
            'insuranceVerification': updated_patient.insurance_verification,
            'familyAndPatientAware': updated_patient.family_and_patient_aware,
            'inPersonVisit': updated_patient.in_person_visit,
            'dischargedFromFacility': updated_patient.discharged_from_facility,
            'admitted': updated_patient.admitted,
            'careFollowUp': updated_patient.care_follow_up,
            'formContent': updated_patient.form_content,
            'forms': forms_data,
            'created_at': updated_patient.created_at.isoformat(),
            'updated_at': updated_patient.updated_at.isoformat()
        }
        
        return jsonify({
            'message': 'Case manager record updated successfully',
            'patient': record
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@case_manager_records_bp.route('/<int:record_id>', methods=['DELETE'])
@jwt_required()
def delete_case_manager_record(record_id):
    """Delete a case manager record"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Only allow admin users to delete records
        if user.role_name != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        patient = Patient.query.get(record_id)
        
        if not patient:
            return jsonify({'error': 'Record not found'}), 404
        
        # Delete patient record
        patient_service.delete_patient(patient)
        
        return jsonify({
            'message': 'Case manager record deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
