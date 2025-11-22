from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from app import db, limiter
from app.models.user import User
from app.models.role import Role
from app.services.auth_service import AuthService
from app.utils.validators import validate_user_data, validate_login_data
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import os
import re

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (public endpoint, but admin can create other users)"""
    try:
        data = request.get_json()
        
        # Validate input data
        validation_errors = validate_user_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Check if user already exists (case-insensitive check for better UX)
        existing_username = User.query.filter(db.func.lower(User.username) == db.func.lower(data['username'])).first()
        if existing_username:
            return jsonify({'error': 'Username already exists. Please choose a different username.'}), 400
        
        # Check for existing email (case-insensitive)
        email_to_check = data['email'].strip().lower() if data.get('email') else ''
        existing_email = User.query.filter(db.func.lower(User.email) == db.func.lower(email_to_check)).first()
        if existing_email:
            # Log for debugging (don't expose existing user's email in production)
            import logging
            logging.info(f'Registration attempted with existing email: {email_to_check}')
            return jsonify({
                'error': 'Email already exists. Please use a different email address.',
                'hint': 'If you believe this is an error, the email may already be registered. Try logging in instead.'
            }), 400
        
        # Check if Authorization header is present (optional - for admin registration)
        auth_header = request.headers.get('Authorization')
        is_admin_creating = False
        
        if auth_header and auth_header.startswith('Bearer '):
            try:
                from flask_jwt_extended import decode_token
                token = auth_header.split(' ')[1]
                decoded = decode_token(token)
                current_user_id = decoded.get('sub')
                if current_user_id:
                    current_user = User.query.get(int(current_user_id))
                    is_admin_creating = current_user and current_user.role_name == 'admin'
            except:
                # If token is invalid, treat as public registration
                pass
        
        # For public registration, ensure role is not admin (security measure)
        if not is_admin_creating and (data.get('role') == 'admin' or data.get('role_name') == 'admin'):
            return jsonify({'error': 'Cannot create admin user without admin privileges'}), 403
        
        # Create new user
        try:
            user = auth_service.create_user(data)
        except IntegrityError as e:
            # Handle database unique constraint violations
            db.session.rollback()
            
            # Extract error message from IntegrityError
            error_str = ''
            if hasattr(e, 'orig') and e.orig:
                error_str = str(e.orig).lower()
            elif hasattr(e, 'args') and e.args:
                error_str = str(e.args[0]).lower()
            else:
                error_str = str(e).lower()
            
            # Check if it's a username or email violation
            # PostgreSQL error messages typically include constraint names or field names
            if 'username' in error_str or 'users_username_key' in error_str or 'unique_username' in error_str:
                return jsonify({'error': 'Username already exists. Please choose a different username.'}), 400
            elif 'email' in error_str or 'users_email_key' in error_str or 'unique_email' in error_str:
                return jsonify({'error': 'Email already exists. Please use a different email address.'}), 400
            else:
                # Generic duplicate error - try to be more specific
                if 'duplicate key' in error_str or 'unique constraint' in error_str:
                    return jsonify({'error': 'A user with this information already exists. Please check your username and email.'}), 400
                return jsonify({'error': 'Registration failed. Please try again with different information.'}), 400
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'data': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        # Log the error for debugging
        import logging
        logging.error(f'Registration error: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        
        # Validate input data
        validation_errors = validate_login_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Authenticate user
        user = auth_service.authenticate_user(data['username'], data['password'])
        
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Create access token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already exists'}), 400
            user.email = data['email']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Verify current password
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Set new password
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
@limiter.limit("100 per minute")  # Per-minute limit
@limiter.limit("1000 per day")    # Per-day limit
def get_all_users():
    """Get all users - filtered by home_health_id for admin users"""
    try:
        # Get current user
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Build query - start with active users
        query = User.query.filter_by(is_active=True)
        
        # If user is admin and belongs to a home_health account, filter by home_health_id
        if current_user.role_name == 'admin' and current_user.home_health_id:
            # Admin users can only see users from their same home_health account
            query = query.filter_by(home_health_id=current_user.home_health_id)
        elif current_user.role_name != 'admin':
            # Non-admin users can only see users from their same home_health account
            if current_user.home_health_id:
                query = query.filter_by(home_health_id=current_user.home_health_id)
            else:
                # User without home_health account - return empty or only themselves
                query = query.filter_by(id=current_user.id)
        
        # If admin user has no home_health_id, they can see all users (super admin)
        # This allows for system-wide admin access
        
        users = query.order_by(User.username).all()
        
        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in users]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/roles', methods=['GET'])
def get_roles():
    """Get all available roles"""
    try:
        roles = Role.query.order_by(Role.name).all()
        
        return jsonify({
            'success': True,
            'data': [role.to_dict() for role in roles]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/validate-session', methods=['POST'])
def validate_session():
    """Validate JWT token and return session info"""
    try:
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization header'}), 401
        
        # Extract token
        token = auth_header.split(' ')[1]
        
        # Verify token (this will raise an exception if invalid)
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
        
        # Get user info from token
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Get token info
        jwt_data = get_jwt()
        
        return jsonify({
            'success': True,
            'data': {
                'userId': str(user.id),
                'token': token,
                'expiresAt': datetime.fromtimestamp(jwt_data['exp']).isoformat(),
                'createdAt': datetime.fromtimestamp(jwt_data['iat']).isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Invalid or expired session'}), 401

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (invalidate token)"""
    try:
        # In a real application, you might want to blacklist the token
        # For now, we'll just return success since JWT tokens are stateless
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_token():
    """Refresh JWT token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Create new access token
        new_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'access_token': new_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user information (admin only)"""
    try:
        # Check if current user is admin
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        if not current_user or current_user.role_name != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Validate only the fields that are being updated
        validation_errors = []
        
        # Username validation
        if 'username' in data:
            username = data['username']
            if len(username) < 3:
                validation_errors.append('Username must be at least 3 characters long')
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                validation_errors.append('Username can only contain letters, numbers, and underscores')
        
        # Email validation
        if 'email' in data:
            email = data['email']
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                validation_errors.append('Invalid email format')
        
        # Password validation
        if 'password' in data and data['password']:
            password = data['password']
            if len(password) < 6:
                validation_errors.append('Password must be at least 6 characters long')
            if not re.search(r'[A-Za-z]', password):
                validation_errors.append('Password must contain at least one letter')
            if not re.search(r'\d', password):
                validation_errors.append('Password must contain at least one number')
        
        # Name validation
        if 'first_name' in data and len(data['first_name']) < 2:
            validation_errors.append('First name must be at least 2 characters long')
        
        if 'last_name' in data and len(data['last_name']) < 2:
            validation_errors.append('Last name must be at least 2 characters long')
        
        # Role validation - check role_id or role name
        if 'role_id' in data:
            from app.models.role import Role
            try:
                role_id = int(data['role_id'])
                role = Role.query.get(role_id)
                if not role:
                    valid_roles = [r.name for r in Role.query.all()]
                    validation_errors.append(f'Role ID {role_id} does not exist. Valid roles: {", ".join(valid_roles)}')
            except (ValueError, TypeError):
                validation_errors.append('Role ID must be a valid integer')
        elif 'role' in data:
            from app.models.role import Role
            role = Role.query.filter_by(name=data['role']).first()
            if not role:
                valid_roles = [r.name for r in Role.query.all()]
                validation_errors.append(f'Role must be one of: {", ".join(valid_roles)}')
        
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Update user fields
        if 'username' in data:
            # Check if username is already taken by another user
            existing_user = User.query.filter_by(username=data['username']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Username already exists'}), 400
            user.username = data['username']
        
        if 'email' in data:
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already exists'}), 400
            user.email = data['email']
        
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        # Handle role update - use role_id or role name
        if 'role_id' in data:
            from app.models.role import Role
            try:
                role_id = int(data['role_id'])
                role = Role.query.get(role_id)
                if role:
                    user.role_id = role_id
            except (ValueError, TypeError):
                pass  # Invalid role_id, skip
        elif 'role' in data:
            from app.models.role import Role
            role = Role.query.filter_by(name=data['role']).first()
            if role:
                user.role_id = role.id
        if 'facility_name' in data:
            # Handle facility_name - get or create facility
            from app.models.facility import Facility
            facility_name = data['facility_name']
            if facility_name:
                facility = Facility.get_or_create(
                    name=facility_name,
                    address=data.get('facility_address'),
                    phone=data.get('facility_phone')
                )
                user.facility_id = facility.id
            else:
                user.facility_id = None
        elif 'facility_id' in data:
            # Convert facility_id to integer if it's provided
            facility_id = data['facility_id']
            if facility_id and str(facility_id).strip():
                try:
                    user.facility_id = int(facility_id)
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid facility_id format'}), 400
            else:
                user.facility_id = None
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'data': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        # Validate user_id
        if user_id is None:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Check if current user is admin
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        if not current_user or current_user.role_name != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Prevent admin from deleting themselves
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        # Soft delete by setting is_active to False
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
