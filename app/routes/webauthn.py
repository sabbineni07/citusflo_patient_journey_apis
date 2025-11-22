from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app import db, limiter
from app.models.user import User
from app.services.webauthn_service import WebAuthnService
from datetime import datetime
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

webauthn_bp = Blueprint('webauthn', __name__)
webauthn_service = WebAuthnService()


def _resolve_relying_party_info():
    """Determine relying party id/name based on request origin and configuration."""
    origin = request.headers.get('Origin', '')
    default_rp_id = current_app.config.get('WEBAUTHN_RP_ID', 'api.citusflo.com')
    default_rp_name = current_app.config.get('WEBAUTHN_RP_NAME', 'Patient Journey App')

    if origin:
        parsed = urlparse(origin)
        hostname = parsed.hostname
        if hostname:
            rp_id = hostname
            rp_name_override = current_app.config.get('WEBAUTHN_RP_NAME')
            rp_name = rp_name_override or hostname
            return rp_id, rp_name

    return default_rp_id, default_rp_name


# ---------------------------------------------------------------------------
# Preflight (CORS) handlers
# ---------------------------------------------------------------------------
@webauthn_bp.route('/register/begin', methods=['OPTIONS'])
def register_begin_options():
    return '', 204


@webauthn_bp.route('/register/complete', methods=['OPTIONS'])
def register_complete_options():
    return '', 204


@webauthn_bp.route('/authenticate/begin', methods=['OPTIONS'])
def authenticate_begin_options():
    return '', 204


@webauthn_bp.route('/authenticate/complete', methods=['OPTIONS'])
def authenticate_complete_options():
    return '', 204


@webauthn_bp.route('/credentials', methods=['OPTIONS'])
@webauthn_bp.route('/credentials/<credential_id>', methods=['OPTIONS'])
def credentials_options(credential_id=None):
    return '', 204

# Rate limiting for WebAuthn endpoints
@webauthn_bp.route('/register/begin', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def begin_registration():
    """Begin WebAuthn registration - generate challenge and options"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            logger.warning(f"Registration begin: User {user_id} not found")
            return jsonify({'error': 'User not found'}), 404
        
        rp_id, rp_name = _resolve_relying_party_info()

        options, challenge = webauthn_service.create_registration_options(
            user_id=user_id,
            username=user.username,
            display_name=f"{user.first_name} {user.last_name}",
            rp_id=rp_id,
            rp_name=rp_name
        )
        
        logger.info(f"Registration begin successful for user {user_id}")
        return jsonify({
            'success': True,
            'options': options,
            'challenge': challenge
        }), 200
        
    except Exception as e:
        logger.error(f"Error in begin_registration: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/register/complete', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def complete_registration():
    """Complete WebAuthn registration - verify and store credential"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        if not data:
            logger.warning("Registration complete: No data provided")
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['credential_id', 'public_key', 'attestation_object', 
                          'client_data_json', 'challenge']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.warning(f"Registration complete: Missing fields: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        credential = webauthn_service.verify_registration(
            user_id=user_id,
            credential_id=data['credential_id'],
            public_key=data['public_key'],
            attestation_object=data['attestation_object'],
            client_data_json=data['client_data_json'],
            challenge=data['challenge']
        )
        
        logger.info(f"Registration complete successful for user {user_id}")
        return jsonify({
            'success': True,
            'message': 'WebAuthn credential registered successfully',
            'data': credential.to_dict()
        }), 201
        
    except ValueError as e:
        logger.warning(f"Registration complete validation error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in complete_registration: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

@webauthn_bp.route('/authenticate/begin', methods=['POST'])
@limiter.limit("20 per minute")
def begin_authentication():
    """Begin WebAuthn authentication - generate challenge"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        if user_id:
            try:
                user_id = int(user_id)
                user = User.query.get(user_id)
                if not user:
                    logger.warning(f"Authentication begin: User {user_id} not found")
                    return jsonify({'error': 'User not found'}), 404
            except (ValueError, TypeError):
                logger.warning(f"Authentication begin: Invalid user_id: {user_id}")
                return jsonify({'error': 'Invalid user_id'}), 400
        
        rp_id, _ = _resolve_relying_party_info()

        options, challenge = webauthn_service.create_authentication_options(
            user_id=user_id if user_id else None,
            rp_id=rp_id
        )
        
        logger.info(f"Authentication begin successful for user {user_id or 'discoverable'}")
        return jsonify({
            'success': True,
            'options': options,
            'challenge': challenge
        }), 200
        
    except Exception as e:
        logger.error(f"Error in begin_authentication: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/authenticate/complete', methods=['POST'])
@limiter.limit("10 per minute")
def complete_authentication():
    """Complete WebAuthn authentication - verify assertion"""
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("Authentication complete: No data provided")
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['credential_id', 'authenticator_data', 'client_data_json', 'signature']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.warning(f"Authentication complete: Missing fields: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Try to find credential by credential_id
        from app.models.webauthn_credential import WebAuthnCredential
        credential = WebAuthnCredential.query.filter_by(credential_id=data['credential_id']).first()
        
        if not credential:
            logger.warning(f"Authentication complete: Credential not found: {data['credential_id'][:20]}...")
            return jsonify({'error': 'Credential not found'}), 404
        
        # Verify authentication (this will update counter)
        verified_credential = webauthn_service.verify_authentication(
            credential_id=data['credential_id'],
            authenticator_data=data['authenticator_data'],
            client_data_json=data['client_data_json'],
            signature=data['signature'],
            user_handle=data.get('user_handle')
        )
        
        user = User.query.get(verified_credential.user_id)
        if not user or not user.is_active:
            logger.warning(f"Authentication complete: User {verified_credential.user_id} not found or inactive")
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Create JWT token for the authenticated user
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(user.id))
        
        logger.info(f"Authentication complete successful for user {user.id}")
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except ValueError as e:
        logger.warning(f"Authentication complete validation error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in complete_authentication: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Authentication failed. Please try again.'}), 500

@webauthn_bp.route('/credentials', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_credentials():
    """Get all WebAuthn credentials for current user"""
    try:
        user_id = int(get_jwt_identity())
        credentials = webauthn_service.get_user_credentials(user_id)
        
        logger.info(f"Retrieved {len(credentials)} credentials for user {user_id}")
        return jsonify({
            'success': True,
            'data': [cred.to_dict() for cred in credentials]
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_credentials: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/credentials/<credential_id>', methods=['DELETE'])
@jwt_required()
@limiter.limit("10 per minute")
def delete_credential(credential_id):
    """Delete a WebAuthn credential"""
    try:
        user_id = int(get_jwt_identity())
        webauthn_service.delete_credential(credential_id, user_id)
        
        logger.info(f"Deleted credential {credential_id[:20]}... for user {user_id}")
        return jsonify({
            'success': True,
            'message': 'Credential deleted successfully'
        }), 200
        
    except ValueError as e:
        logger.warning(f"Delete credential validation error: {e}")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in delete_credential: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/has-credentials/<int:user_id>', methods=['GET'])
@limiter.limit("30 per minute")
def check_has_credentials(user_id):
    """Check if user has WebAuthn credentials (public endpoint for user selection)"""
    try:
        has_credentials = webauthn_service.user_has_credentials(user_id)
        
        return jsonify({
            'success': True,
            'has_credentials': has_credentials
        }), 200
        
    except Exception as e:
        logger.error(f"Error in check_has_credentials: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
