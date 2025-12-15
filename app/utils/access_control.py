"""
Access control utilities for role-based access control (RBAC)
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility
from app import db


def require_role(*allowed_roles):
    """
    Decorator to require specific roles for an endpoint.
    
    Usage:
        @require_role('admin', 'clinician')
        @jwt_required()
        def some_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user_id = get_jwt_identity()
            current_user = User.query.get(int(current_user_id))
            
            if not current_user:
                return jsonify({'error': 'User not found'}), 404
            
            if current_user.role_name not in allowed_roles:
                return jsonify({
                    'error': 'Access denied. Required role: {}'.format(', '.join(allowed_roles))
                }), 403
            
            # Attach current_user to kwargs for use in the route
            kwargs['current_user'] = current_user
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(permission):
    """
    Decorator to require specific permissions for an endpoint.
    
    Permissions:
        - 'read': Read access
        - 'write': Create/Update access
        - 'delete': Delete access
        - 'patient_only': Access to patient endpoints only
    
    Usage:
        @require_permission('write')
        @jwt_required()
        def create_patient():
            ...
    """
    role_permissions = {
        'case_manager': ['read'],
        'super_admin': ['read', 'write', 'delete'],
        'admin': ['read', 'write', 'delete'],
        'clinician': ['read', 'write']
    }
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user_id = get_jwt_identity()
            current_user = User.query.get(int(current_user_id))
            
            if not current_user:
                return jsonify({'error': 'User not found'}), 404
            
            user_role = current_user.role_name
            allowed_permissions = role_permissions.get(user_role, [])
            
            if permission not in allowed_permissions:
                return jsonify({
                    'error': f'Access denied. Permission "{permission}" required.'
                }), 403
            
            kwargs['current_user'] = current_user
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def filter_patients_by_access(query, current_user):
    """
    Filter patients query based on user's role and access level.
    
    Args:
        query: SQLAlchemy query object for Patient
        current_user: User object
    
    Returns:
        Filtered query object
    """
    role_name = current_user.role_name
    
    if role_name == 'case_manager':
        # case_manager can only see patients from their facility
        if current_user.facility_id:
            query = query.filter(Patient.facility_id == current_user.facility_id)
        else:
            # If no facility_id, return empty query
            query = query.filter(Patient.id == None)  # This will return no results
    
    elif role_name in ['super_admin', 'admin', 'clinician']:
        # super_admin, admin and clinician can see all patients from their home_health
        # super_admin without home_health_id can see all patients
        if role_name == 'super_admin' and not current_user.home_health_id:
            # super_admin without home_health_id can see all patients
            pass  # No filtering - show all
        elif current_user.home_health_id:
            query = query.filter(Patient.home_health_id == current_user.home_health_id)
        else:
            # If no home_health_id (and not super_admin), return empty query
            query = query.filter(Patient.id == None)
    
    else:
        # Unknown role - no access
        query = query.filter(Patient.id == None)
    
    return query


def filter_facilities_by_access(query, current_user):
    """
    Filter facilities query based on user's role and access level.
    
    Args:
        query: SQLAlchemy query object for Facility
        current_user: User object
    
    Returns:
        Filtered query object
    """
    role_name = current_user.role_name
    
    if role_name == 'case_manager':
        # case_manager can only see their facility
        if current_user.facility_id:
            query = query.filter(Facility.id == current_user.facility_id)
        # else:
        #     query = query.filter(Facility.id == None)
    
    elif role_name in ['super_admin', 'admin', 'clinician']:
        # super_admin, admin and clinician can see facilities from hospitals that work with their home_health
        # super_admin without home_health_id can see all facilities
        if role_name == 'super_admin' and not current_user.home_health_id:
            # super_admin without home_health_id can see all facilities
            pass  # No filtering - show all
        elif current_user.home_health_id:
            # Get hospital IDs that work with this home_health
            from app.models.hospital import Hospital
            from app.models.home_health import HomeHealth
            
            home_health = HomeHealth.query.get(current_user.home_health_id)
            if home_health:
                hospital_ids = [h.id for h in home_health.hospitals]
                if hospital_ids:
                    query = query.filter(Facility.hospital_id.in_(hospital_ids))
                # else:
                #     query = query.filter(Facility.id == None)
            # else:
            #     query = query.filter(Facility.id == None)
        # else:
        #     query = query.filter(Facility.id == None)
    # else:
    #     query = query.filter(Facility.id == None)
    
    return query


def can_access_patient(current_user, patient):
    """
    Check if current user can access a specific patient.
    
    Args:
        current_user: User object
        patient: Patient object
    
    Returns:
        bool: True if user can access patient, False otherwise
    """
    role_name = current_user.role_name
    
    if role_name == 'case_manager':
        # case_manager can only access patients from their facility
        return (patient.facility_id == current_user.facility_id)
    
    elif role_name in ['super_admin', 'admin', 'clinician']:
        # super_admin, admin and clinician can access patients from their home_health
        # super_admin without home_health_id can access all patients
        if role_name == 'super_admin' and not current_user.home_health_id:
            return True  # super_admin can access all patients
        return (patient.home_health_id == current_user.home_health_id)
    
    return False


def can_modify_patient(current_user, patient):
    """
    Check if current user can modify (update/delete) a specific patient.
    
    Args:
        current_user: User object
        patient: Patient object
    
    Returns:
        bool: True if user can modify patient, False otherwise
    """
    role_name = current_user.role_name
    
    # case_manager cannot modify anything (read-only)
    if role_name == 'case_manager':
        return False
    
    # super_admin can modify all patients (if no home_health_id) or patients from their home_health
    if role_name == 'super_admin':
        if not current_user.home_health_id:
            return True  # super_admin can modify all patients
        return (patient.home_health_id == current_user.home_health_id)
    
    # admin can modify patients from their home_health
    if role_name == 'admin':
        return (patient.home_health_id == current_user.home_health_id)
    
    # clinician can update (but not delete) patients from their home_health
    if role_name == 'clinician':
        return (patient.home_health_id == current_user.home_health_id)
    
    return False


def can_create_patient(current_user):
    """
    Check if current user can create patients.
    
    Args:
        current_user: User object
    
    Returns:
        bool: True if user can create patients, False otherwise
    """
    role_name = current_user.role_name
    
    # super_admin, admin and clinician can create patients
    if role_name in ['super_admin', 'admin', 'clinician']:
        return True
    
    # case_manager cannot create patients (read-only)
    return False


def can_delete_patient(current_user, patient):
    """
    Check if current user can delete a specific patient.
    
    Args:
        current_user: User object
        patient: Patient object
    
    Returns:
        bool: True if user can delete patient, False otherwise
    """
    role_name = current_user.role_name
    
    # super_admin and admin can delete patients
    if role_name == 'super_admin':
        if not current_user.home_health_id:
            return True  # super_admin can delete all patients
        return (patient.home_health_id == current_user.home_health_id)
    
    if role_name == 'admin':
        return (patient.home_health_id == current_user.home_health_id)
    
    # case_manager and clinician cannot delete patients
    return False

