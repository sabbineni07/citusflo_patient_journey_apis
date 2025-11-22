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

patients_bp = Blueprint('patients', __name__)
patient_service = PatientService()

@patients_bp.route('/', methods=['GET'])
@jwt_required()
def get_patients():
    """Get all patients with optional filtering and pagination - filtered by access control"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        
        # Start with base query
        query = Patient.query
        
        # Apply access control filtering
        query = filter_patients_by_access(query, user)
        
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
        
        # Get total count after filtering
        total = query.count()
        
        # Apply pagination
        patients = query.order_by(Patient.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        ).items
        
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
    """Get a specific patient by ID - with access control"""
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
        
        return jsonify({
            'patient': patient.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@patients_bp.route('/', methods=['POST'])
@jwt_required()
def create_patient():
    """Create a new patient - admin and clinician"""
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
            db.session.commit()
        
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
    """Update an existing patient - admin and clinician only"""
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

