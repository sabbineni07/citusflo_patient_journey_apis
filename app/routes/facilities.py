from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.facility import Facility
from app.utils.access_control import filter_facilities_by_access

facilities_bp = Blueprint('facilities', __name__)

@facilities_bp.route('/', methods=['GET'])
@jwt_required()
def get_facilities():
    """Get all facilities - filtered by access control"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Block clinician access (patient-only)
        if user.role_name == 'clinician':
            return jsonify({'error': 'Access denied. Clinicians can only access patient data.'}), 403
        
        # Start with base query
        query = Facility.query
        
        # Apply access control filtering
        query = filter_facilities_by_access(query, user)
        
        # Order by name
        facilities = query.order_by(Facility.name).all()
        facilities_data = [facility.to_dict() for facility in facilities]
        
        return jsonify({
            'success': True,
            'data': facilities_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@facilities_bp.route('/<facility_id>', methods=['GET'])
@jwt_required()
def get_facility(facility_id):
    """Get a specific facility by ID - with access control"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Block clinician access (patient-only)
        if user.role_name == 'clinician':
            return jsonify({'error': 'Access denied. Clinicians can only access patient data.'}), 403
        
        facility = Facility.query.get(int(facility_id))
        
        if not facility:
            return jsonify({'error': 'Facility not found'}), 404
        
        # Check if user has access to this facility
        query = Facility.query.filter(Facility.id == facility.id)
        query = filter_facilities_by_access(query, user)
        
        if not query.first():
            return jsonify({'error': 'Access denied. You do not have permission to view this facility.'}), 403
        
        return jsonify({
            'success': True,
            'data': facility.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
