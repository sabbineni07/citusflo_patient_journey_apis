from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.patient import Patient
from app.services.patient_service import PatientService
from datetime import datetime, timedelta

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
        
        # Build query
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
        
        # Transform to case manager records format
        records = []
        for patient in patients:
            record = {
                'id': patient.id,
                'caseManagerName': patient.case_manager_name,
                'phoneNumber': patient.phone_number,
                'facilityName': patient.facility_name,
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
        
        record = {
            'id': patient.id,
            'caseManagerName': patient.case_manager_name,
            'phoneNumber': patient.phone_number,
            'facilityName': patient.facility_name,
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
        
        # Build base query
        query = Patient.query
        
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
