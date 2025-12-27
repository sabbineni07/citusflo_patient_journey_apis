from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.patient import Patient
from app.models.patient_form import PatientForm
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditResourceType
from app.utils.access_control import can_modify_patient, can_access_patient
from datetime import datetime
import re

patient_forms_bp = Blueprint('patient_forms', __name__)


@patient_forms_bp.route('/<int:patient_id>/forms/', methods=['GET'])
@jwt_required()
def get_patient_forms(patient_id):
    """Get all forms for a specific patient
    
    Query Parameters:
        - form_type: Filter by form type (optional)
        - latest_only: If true, return only latest version of each form_id (default: true)
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
            AuditService.log_patient_form_access(
                user_id=user.id,
                username=user.username,
                action=AuditActionType.ACCESS_DENIED,
                form_id=None,
                patient_id=patient_id,
                success=False,
                error_message='Access denied - insufficient permissions'
            )
            return jsonify({'error': 'Access denied. You do not have permission to view forms for this patient.'}), 403
        
        # Get query parameters
        form_type = request.args.get('form_type')
        latest_only = request.args.get('latest_only', 'true').lower() == 'true'
        
        # Build query
        query = PatientForm.query.filter_by(patient_id=patient_id)
        
        if form_type:
            query = query.filter_by(form_type=form_type)
        
        if latest_only:
            # Get latest version of each form_id
            forms = patient.get_latest_forms()
        else:
            # Get all forms (with versioning)
            forms = query.order_by(PatientForm.created_at.desc()).all()
        
        # Audit log: Patient forms accessed
        AuditService.log_patient_form_access(
            user_id=user.id,
            username=user.username,
            action=AuditActionType.READ,
            form_id=None,
            patient_id=patient_id,
            success=True,
            details={'count': len(forms), 'form_type_filter': form_type, 'latest_only': latest_only}
        )
        
        return jsonify({
            'forms': [form.to_dict() for form in forms],
            'total': len(forms),
            'patient_id': patient_id
        }), 200
        
    except Exception as e:
        import logging
        logging.error(f'Error in get_patient_forms: {str(e)}', exc_info=True)
        return jsonify({'error': 'An error occurred while retrieving patient forms. Please try again.'}), 500


@patient_forms_bp.route('/<int:patient_id>/forms/<int:form_id>', methods=['GET'])
@jwt_required()
def get_patient_form(patient_id, form_id):
    """Get a specific form by patient_id and form_id (returns latest version)"""
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
            AuditService.log_patient_form_access(
                user_id=user.id,
                username=user.username,
                action=AuditActionType.ACCESS_DENIED,
                form_id=form_id,
                patient_id=patient_id,
                success=False,
                error_message='Access denied - insufficient permissions'
            )
            return jsonify({'error': 'Access denied. You do not have permission to view this form.'}), 403
        
        # Get latest version of the form
        patient_form = PatientForm.query.filter_by(
            patient_id=patient_id,
            form_id=form_id
        ).order_by(PatientForm.created_at.desc()).first()
        
        if not patient_form:
            return jsonify({'error': 'Patient form not found'}), 404
        
        # Audit log: Patient form accessed
        AuditService.log_patient_form_access(
            user_id=user.id,
            username=user.username,
            action=AuditActionType.READ,
            form_id=form_id,
            patient_id=patient_id,
            success=True
        )
        
        return jsonify({
            'form': patient_form.to_dict(),
            'patient_id': patient_id
        }), 200
        
    except Exception as e:
        import logging
        logging.error(f'Error in get_patient_form: {str(e)}', exc_info=True)
        return jsonify({'error': 'An error occurred while retrieving the patient form. Please try again.'}), 500


@patient_forms_bp.route('/<int:patient_id>/forms/', methods=['POST'])
@jwt_required()
def create_patient_form(patient_id):
    """Create a new patient form
    
    Request Body:
    {
      "formType": "intake",
      "formData": {...},
      "formId": 5  // Optional - if not provided, generates new form_id
                     // If formId is provided and form exists, creates new version (update)
    }
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
            AuditService.log_patient_form_access(
                user_id=user.id,
                username=user.username,
                action=AuditActionType.ACCESS_DENIED,
                form_id=None,
                patient_id=patient_id,
                success=False,
                error_message='Access denied - insufficient permissions to create form'
            )
            return jsonify({'error': 'Access denied. You do not have permission to create forms for this patient.'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Extract form data
        form_type = data.get('formType') or data.get('form_type') or data.get('type')
        form_data = data.get('formData') or data.get('form_data') or data.get('data', {})
        form_id = data.get('formId') or data.get('form_id') or data.get('id')
        
        # Log request for debugging
        import logging
        logging.info(f'POST /api/patients/{patient_id}/forms/ - Request data: formType={form_type}, formId={form_id}, hasFormData={form_data is not None}')
        
        if not form_type:
            return jsonify({'error': 'formType is required'}), 400
        
        if not isinstance(form_data, dict):
            form_data = {'value': form_data} if form_data is not None else {}
        
        # Handle form_id
        INTEGER_MAX = 2147483647  # PostgreSQL INTEGER maximum value
        form_id_int = None
        
        if form_id is not None:
            try:
                # Try direct conversion
                if isinstance(form_id, str):
                    # Try to extract number if it's a string like 'form-1766197035107'
                    match = re.search(r'(\d+)$', form_id)
                    if match:
                        extracted_value = int(match.group(1))
                        if extracted_value <= INTEGER_MAX and extracted_value >= -2147483648:
                            form_id_int = extracted_value
                    elif form_id.isdigit():
                        form_id_int = int(form_id)
                        if form_id_int > INTEGER_MAX:
                            form_id_int = None
                else:
                    form_id_int = int(form_id)
                    if form_id_int > INTEGER_MAX:
                        form_id_int = None
            except (ValueError, TypeError):
                form_id_int = None
        
        # Generate new form_id if not provided or invalid
        if form_id_int is None:
            from sqlalchemy import func
            max_form_id = db.session.query(func.max(PatientForm.form_id)).filter_by(
                patient_id=patient_id
            ).scalar()
            form_id_int = (max_form_id or 0) + 1
            logging.info(f'Generated new form_id: {form_id_int} for patient {patient_id}')
        else:
            # Check if form with this form_id already exists
            existing_form = PatientForm.query.filter_by(
                patient_id=patient_id,
                form_id=form_id_int
            ).first()
            if existing_form:
                logging.info(f'Form with form_id {form_id_int} exists for patient {patient_id} - creating new version (update via POST)')
        
        # Create new form (versioning - always creates new record)
        # This handles both new forms and updates (creates new version with same form_id)
        patient_form = PatientForm(
            form_id=form_id_int,
            patient_id=patient_id,
            form_type=str(form_type),
            form_data=form_data,
            created_by=user.id
        )
        
        db.session.add(patient_form)
        db.session.commit()
        
        # Determine if this was an update (form_id existed) or new form
        is_update = PatientForm.query.filter_by(
            patient_id=patient_id,
            form_id=form_id_int
        ).count() > 1  # More than 1 means we just created a new version
        
        action_type = AuditActionType.UPDATE if is_update else AuditActionType.CREATE
        
        # Audit log: Patient form created or updated
        AuditService.log_patient_form_access(
            user_id=user.id,
            username=user.username,
            action=action_type,
            form_id=form_id_int,
            patient_id=patient_id,
            success=True,
            details={'form_type': form_type, 'is_update': is_update}
        )
        
        message = 'Patient form updated successfully (new version created)' if is_update else 'Patient form created successfully'
        
        return jsonify({
            'message': message,
            'form': patient_form.to_dict(),
            'patient_id': patient_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f'Error in create_patient_form: {str(e)}', exc_info=True)
        
        # Audit log: Patient form creation failed
        try:
            AuditService.log_patient_form_access(
                user_id=user.id if user else None,
                username=user.username if user else None,
                action=AuditActionType.CREATE,
                form_id=None,
                patient_id=patient_id,
                success=False,
                error_message=str(e)[:500] if str(e) else 'Unknown error'
            )
        except:
            pass
        
        return jsonify({'error': 'An error occurred while creating the patient form. Please try again.'}), 500


@patient_forms_bp.route('/<int:patient_id>/forms/<int:form_id>', methods=['PUT'])
@jwt_required()
def update_patient_form(patient_id, form_id):
    """Update a patient form (creates new version)
    
    Request Body:
    {
      "formType": "intake",  // Optional - if not provided, keeps existing
      "formData": {...}       // Required - new form data
      "formId": 5            // Optional - should match URL parameter (ignored if different)
    }
    
    Note: Also accepts formId in body for frontend compatibility, but URL form_id takes precedence
    """
    try:
        import logging
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Check if user can modify this patient
        if not can_modify_patient(user, patient):
            AuditService.log_patient_form_access(
                user_id=user.id,
                username=user.username,
                action=AuditActionType.ACCESS_DENIED,
                form_id=form_id,
                patient_id=patient_id,
                success=False,
                error_message='Access denied - insufficient permissions to update form'
            )
            return jsonify({'error': 'Access denied. You do not have permission to update forms for this patient.'}), 403
        
        # Get existing form to preserve form_type if not provided
        existing_form = PatientForm.query.filter_by(
            patient_id=patient_id,
            form_id=form_id
        ).order_by(PatientForm.created_at.desc()).first()
        
        if not existing_form:
            return jsonify({'error': 'Patient form not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Log request for debugging
        body_form_id = data.get('formId') or data.get('form_id') or data.get('id')
        logging.info(f'PUT /api/patients/{patient_id}/forms/{form_id} - URL form_id: {form_id}, Body formId: {body_form_id}')
        
        # Extract form data
        form_type = data.get('formType') or data.get('form_type') or data.get('type') or existing_form.form_type
        form_data = data.get('formData') or data.get('form_data') or data.get('data')
        
        if form_data is None:
            return jsonify({'error': 'formData is required'}), 400
        
        if not isinstance(form_data, dict):
            form_data = {'value': form_data} if form_data is not None else {}
        
        # Create new version of the form (versioning)
        # Use form_id from URL (preferred) or from body if URL doesn't match (for compatibility)
        form_id_to_use = form_id  # URL parameter takes precedence
        
        updated_form = PatientForm(
            form_id=form_id_to_use,
            patient_id=patient_id,
            form_type=str(form_type),
            form_data=form_data,
            created_by=user.id
        )
        
        db.session.add(updated_form)
        db.session.commit()
        
        logging.info(f'Created new version of form_id {form_id_to_use} for patient {patient_id}')
        
        # Audit log: Patient form updated
        AuditService.log_patient_form_access(
            user_id=user.id,
            username=user.username,
            action=AuditActionType.UPDATE,
            form_id=form_id_to_use,
            patient_id=patient_id,
            success=True,
            details={'form_type': form_type}
        )
        
        return jsonify({
            'message': 'Patient form updated successfully (new version created)',
            'form': updated_form.to_dict(),
            'patient_id': patient_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f'Error in update_patient_form: {str(e)}', exc_info=True)
        
        # Audit log: Patient form update failed
        try:
            AuditService.log_patient_form_access(
                user_id=user.id if user else None,
                username=user.username if user else None,
                action=AuditActionType.UPDATE,
                form_id=form_id,
                patient_id=patient_id,
                success=False,
                error_message=str(e)[:500] if str(e) else 'Unknown error'
            )
        except:
            pass
        
        return jsonify({'error': 'An error occurred while updating the patient form. Please try again.'}), 500


@patient_forms_bp.route('/<int:patient_id>/forms/<int:form_id>', methods=['DELETE'])
@jwt_required()
def delete_patient_form(patient_id, form_id):
    """Delete a patient form by patient_id and form_id - admin and clinician
    
    Deletes ALL versions of the form with the specified form_id
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Check if user can modify this patient (admin and clinician)
        if not can_modify_patient(user, patient):
            # Audit log: Access denied
            AuditService.log_patient_form_access(
                user_id=user.id,
                username=user.username,
                action=AuditActionType.ACCESS_DENIED,
                form_id=form_id,
                patient_id=patient_id,
                success=False,
                error_message='Access denied - insufficient permissions to delete form'
            )
            return jsonify({
                'error': 'Access denied. You do not have permission to delete forms for this patient.'
            }), 403
        
        # Get the patient form to log form_type before deletion
        patient_form = PatientForm.query.filter_by(
            patient_id=patient_id,
            form_id=form_id
        ).first()
        
        if not patient_form:
            return jsonify({'error': 'Patient form not found'}), 404
        
        # Store form details for audit log before deletion
        form_type = patient_form.form_type
        
        # Delete all versions of this form (all records with this form_id for this patient)
        deleted_count = PatientForm.query.filter_by(
            patient_id=patient_id,
            form_id=form_id
        ).delete()
        
        db.session.commit()
        
        # Audit log: Patient form deleted
        AuditService.log_patient_form_access(
            user_id=user.id,
            username=user.username,
            action=AuditActionType.DELETE,
            form_id=form_id,
            patient_id=patient_id,
            success=True,
            details={'form_type': form_type, 'deleted_versions': deleted_count}
        )
        
        return jsonify({
            'message': 'Patient form deleted successfully',
            'form_id': form_id,
            'patient_id': patient_id,
            'deleted_versions': deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f'Error deleting patient form: {str(e)}', exc_info=True)
        
        # Audit log: Patient form deletion failed
        try:
            AuditService.log_patient_form_access(
                user_id=user.id if user else None,
                username=user.username if user else None,
                action=AuditActionType.DELETE,
                form_id=form_id,
                patient_id=patient_id,
                success=False,
                error_message=str(e)[:500] if str(e) else 'Unknown error'
            )
        except:
            pass  # Don't fail on audit log errors
        
        return jsonify({'error': 'An error occurred while deleting the patient form. Please try again.'}), 500

