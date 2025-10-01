from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.facility import Facility

facilities_bp = Blueprint('facilities', __name__)

@facilities_bp.route('/', methods=['GET'])
@jwt_required()
def get_facilities():
    """Get all facilities"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get all facilities from database
        facilities = Facility.query.order_by(Facility.name).all()
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
    """Get a specific facility by ID"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        facility = Facility.query.get(int(facility_id))
        
        if not facility:
            return jsonify({'error': 'Facility not found'}), 404
        
        return jsonify({
            'success': True,
            'data': facility.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
