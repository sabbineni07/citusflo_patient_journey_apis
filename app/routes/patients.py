from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from sqlalchemy import or_
from app.models.user import User
from app.models.patient import Patient
from app.services.patient_service import PatientService
from app.utils.validators import validate_patient_data
from app.utils.access_control import (
    filter_patients_by_access,
    can_access_patient,
    can_modify_patient,
    can_create_patient,
    can_delete_patient
)
from datetime import datetime
import json as json_module

patients_bp = Blueprint('patients', __name__)
patient_service = PatientService()


def _transform_patient_to_camel_case(patient):
    """Transform patient to camelCase format for case manager records compatibility"""
    # Handle forms - ensure it's always a list
    forms_data = patient.forms if patient.forms is not None else []
    if isinstance(forms_data, str):
        try:
            forms_data = json_module.loads(forms_data)
        except (json_module.JSONDecodeError, TypeError):
            forms_data = []
    if not isinstance(forms_data, list):
        forms_data = []
    
    return {
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
        'forms': forms_data,
        'created_at': patient.created_at.isoformat() if patient.created_at else None,
        'updated_at': patient.updated_at.isoformat() if patient.updated_at else None
    }


@patients_bp.route('/', methods=['GET'])
@jwt_required()
def get_patients():
    """Get all patients with optional filtering and pagination - filtered by access control
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 10)
        - search: Search term for patient name, case manager, facility, or phone
        - date_from: Start date filter (ISO format, optional)
        - date_to: End date filter (ISO format, optional)
        - facility_id: Filter by facility ID (optional)
        - format: Response format - 'camelCase' for case manager format, 'default' for standard format (default: 'default')
    """
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
        response_format = request.args.get('format', 'default')  # 'camelCase' or 'default'
        
        # Start with base query
        query = Patient.query
        
        # Apply access control filtering
        query = filter_patients_by_access(query, user)
        
        # Apply additional facility filter if specified (for filtering within allowed scope)
        if facility_id:
            query = query.filter(Patient.facility_id == int(facility_id))
        
        # Apply search filter if provided
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
        
        # Get total count after filtering
        total = query.count()
        
        # Apply pagination
        patients = query.order_by(Patient.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        ).items
        
        # Transform response based on format
        if response_format == 'camelCase':
            # Case manager records format
            records = [_transform_patient_to_camel_case(patient) for patient in patients]
            return jsonify({
                'records': records,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }), 200
        else:
            # Default format
            return jsonify({
                'patients': [patient.to_dict() for patient in patients],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@patients_bp.route('/<int:patient_id>', methods=['GET'])
@jwt_required()
def get_patient(patient_id):
    """Get a specific patient by ID - with access control
    
    Query Parameters:
        - format: Response format - 'camelCase' for case manager format, 'default' for standard format (default: 'default')
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Check if user can access this patient
        if not can_access_patient(user, patient):
            return jsonify({'error': 'Access denied. You do not have permission to view this patient.'}), 403
        
        # Get format parameter
        response_format = request.args.get('format', 'default')
        
        # Transform response based on format
        if response_format == 'camelCase':
            return jsonify({
                'record': _transform_patient_to_camel_case(patient)
            }), 200
        else:
            return jsonify({
                'patient': patient.to_dict()
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@patients_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_patient_stats():
    """Get patient statistics
    
    Query Parameters:
        - date_from: Start date filter (ISO format, optional)
        - date_to: End date filter (ISO format, optional)
        - facility_id: Filter by facility ID (optional)
    """
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
        
        # Apply access control filtering
        query = filter_patients_by_access(query, user)
        
        # Apply additional facility filter if specified
        if facility_id:
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


@patients_bp.route('/', methods=['POST'])
@jwt_required()
def create_patient():
    """Create a new patient - admin and clinician
    
    Query Parameters:
        - format: Response format - 'camelCase' for case manager format, 'default' for standard format (default: 'default')
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user can create patients (admin and clinician)
        if not can_create_patient(user):
            return jsonify({
                'error': 'Access denied. Only administrators and clinicians can create patients.'
            }), 403
        
        data = request.get_json()
        
        # Validate input data
        validation_errors = validate_patient_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Ensure home_health_id is set from current user if not provided
        if 'home_health_id' not in data and user.home_health_id:
            data['home_health_id'] = user.home_health_id
        
        # Create new patient
        patient = patient_service.create_patient(data, int(user_id))
        
        # If home_health_id was not set in patient service, set it now
        if not patient.home_health_id and user.home_health_id:
            patient.home_health_id = user.home_health_id
        
        # Handle forms if provided
        if 'forms' in data and data['forms']:
            if isinstance(data['forms'], list):
                patient.forms = data['forms']
            else:
                patient.forms = []
        else:
            patient.forms = []
        
        db.session.commit()
        
        # Get format parameter
        response_format = request.args.get('format', 'default')
        
        # Transform response based on format
        if response_format == 'camelCase':
            return jsonify({
                'message': 'Patient created successfully',
                'patient': _transform_patient_to_camel_case(patient)
            }), 201
        else:
            return jsonify({
                'message': 'Patient created successfully',
                'patient': patient.to_dict()
            }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@patients_bp.route('/<int:patient_id>', methods=['PUT'])
@jwt_required()
def update_patient(patient_id):
    """Update an existing patient - admin and clinician only
    
    Query Parameters:
        - format: Response format - 'camelCase' for case manager format, 'default' for standard format (default: 'default')
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Check if user can modify this patient
        if not can_modify_patient(user, patient):
            return jsonify({
                'error': 'Access denied. You do not have permission to modify this patient.'
            }), 403
        
        data = request.get_json()
        
        # Validate input data
        validation_errors = validate_patient_data(data, is_update=True)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Update patient
        updated_patient = patient_service.update_patient(patient, data)
        
        # Handle forms if provided
        if 'forms' in data:
            if isinstance(data['forms'], list):
                updated_patient.forms = data['forms']
            else:
                updated_patient.forms = []
        
        db.session.commit()
        
        # Get format parameter
        response_format = request.args.get('format', 'default')
        
        # Transform response based on format
        if response_format == 'camelCase':
            return jsonify({
                'message': 'Patient updated successfully',
                'patient': _transform_patient_to_camel_case(updated_patient)
            }), 200
        else:
            return jsonify({
                'message': 'Patient updated successfully',
                'patient': updated_patient.to_dict()
            }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@patients_bp.route('/<int:patient_id>', methods=['DELETE'])
@jwt_required()
def delete_patient(patient_id):
    """Delete a patient - admin only"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Check if user can delete this patient (admin only)
        if not can_delete_patient(user, patient):
            return jsonify({
                'error': 'Access denied. Only administrators can delete patients.'
            }), 403
        
        # Delete patient
        patient_service.delete_patient(patient)
        
        return jsonify({
            'message': 'Patient deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
