"""
Audit service for HIPAA compliance
Provides functions to log all PHI access and modifications
"""
from app import db
from app.models.audit_log import AuditLog, AuditActionType, AuditResourceType
from flask import request
from datetime import datetime
from functools import wraps
from flask_jwt_extended import get_jwt_identity

class AuditService:
    """Service for audit logging"""
    
    @staticmethod
    def get_client_ip():
        """Get client IP address from request"""
        if request:
            # Check for forwarded IP (behind proxy/load balancer)
            forwarded = request.headers.get('X-Forwarded-For')
            if forwarded:
                # X-Forwarded-For can contain multiple IPs, take the first one
                return forwarded.split(',')[0].strip()
            return request.remote_addr or 'unknown'
        return 'unknown'
    
    @staticmethod
    def get_user_agent():
        """Get user agent from request"""
        if request:
            return request.headers.get('User-Agent', 'unknown')
        return 'unknown'
    
    @staticmethod
    def log_action(
        user_id=None,
        username=None,
        action: AuditActionType = None,
        resource_type: AuditResourceType = None,
        resource_id=None,
        success=True,
        error_message=None,
        details=None,
        ip_address=None,
        user_agent=None
    ):
        """
        Log an audit event
        
        Args:
            user_id: ID of the user performing the action (optional)
            username: Username for historical reference (optional, will fetch if user_id provided)
            action: Type of action (AuditActionType enum)
            resource_type: Type of resource (AuditResourceType enum)
            resource_id: ID of the resource (patient_id, user_id, etc.)
            success: Whether the action was successful
            error_message: Error message if failed (must not contain PHI)
            details: Additional context as dict (must not contain PHI)
            ip_address: IP address (will fetch from request if not provided)
            user_agent: User agent (will fetch from request if not provided)
        """
        try:
            # Get user info if user_id provided
            if user_id and not username:
                from app.models.user import User
                user = User.query.get(user_id)
                if user:
                    username = user.username
            
            # Get IP and user agent if not provided
            if not ip_address:
                ip_address = AuditService.get_client_ip()
            if not user_agent:
                user_agent = AuditService.get_user_agent()
            
            # Convert enums to strings
            action_str = action.value if isinstance(action, AuditActionType) else str(action)
            resource_type_str = resource_type.value if isinstance(resource_type, AuditResourceType) else str(resource_type)
            
            # Create audit log entry
            audit_log = AuditLog(
                user_id=user_id,
                username=username,
                action=action_str,
                resource_type=resource_type_str,
                resource_id=str(resource_id) if resource_id is not None else None,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=AuditService._sanitize_error_message(error_message[:500] if error_message else None),  # Sanitize and limit error message length
                details=details,  # JSON field - ensure no PHI
                created_at=datetime.utcnow()
            )
            
            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            # Never fail the main operation due to audit logging failure
            # Log the error but don't raise
            import logging
            logging.error(f"Failed to create audit log: {str(e)}", exc_info=True)
            # Rollback to avoid transaction issues
            try:
                db.session.rollback()
            except:
                pass
    
    @staticmethod
    def _sanitize_error_message(error_message):
        """
        Sanitize error message to remove any potential PHI
        Removes patterns that might contain PHI (names, dates, IDs, etc.)
        """
        if not error_message:
            return error_message
        
        # List of PHI patterns to remove or redact
        import re
        
        # Remove email addresses
        error_message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', error_message)
        
        # Remove phone numbers (various formats)
        error_message = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', error_message)
        error_message = re.sub(r'\(\d{3}\)\s*\d{3}[-.]?\d{4}', '[PHONE_REDACTED]', error_message)
        
        # Remove dates (various formats)
        error_message = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[DATE_REDACTED]', error_message)
        error_message = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '[DATE_REDACTED]', error_message)
        
        # Remove SSN-like patterns
        error_message = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', error_message)
        
        # Remove common name patterns (capitalized words that might be names)
        # This is less aggressive - only remove if it looks like a full name pattern
        # error_message = re.sub(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', '[NAME_REDACTED]', error_message)
        
        return error_message
    
    @staticmethod
    def log_patient_access(user_id, username, action: AuditActionType, patient_id, success=True, error_message=None, details=None):
        """Log patient record access"""
        AuditService.log_action(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=AuditResourceType.PATIENT,
            resource_id=patient_id,
            success=success,
            error_message=error_message,
            details=details
        )
    
    @staticmethod
    def log_patient_form_access(user_id, username, action: AuditActionType, form_id, patient_id=None, success=True, error_message=None, details=None):
        """Log patient form access"""
        details = details or {}
        if patient_id:
            details['patient_id'] = str(patient_id)
        AuditService.log_action(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=AuditResourceType.PATIENT_FORM,
            resource_id=form_id,
            success=success,
            error_message=error_message,
            details=details
        )
    
    @staticmethod
    def log_authentication(user_id, username, action: AuditActionType, success=True, error_message=None):
        """Log authentication events"""
        AuditService.log_action(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=AuditResourceType.AUTHENTICATION,
            resource_id=None,
            success=success,
            error_message=error_message
        )
    
    @staticmethod
    def log_user_management(user_id, username, action: AuditActionType, target_user_id, success=True, error_message=None, details=None):
        """Log user management actions"""
        AuditService.log_action(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=AuditResourceType.USER,
            resource_id=target_user_id,
            success=success,
            error_message=error_message,
            details=details
        )


def audit_log(action: AuditActionType, resource_type: AuditResourceType, get_resource_id=None, success_callback=None):
    """
    Decorator to automatically log audit events for route handlers
    
    Usage:
        @audit_log(AuditActionType.READ, AuditResourceType.PATIENT, 
                   get_resource_id=lambda: request.view_args.get('patient_id'))
        @jwt_required()
        def get_patient(patient_id):
            ...
    
    Args:
        action: Type of action to log
        resource_type: Type of resource being accessed
        get_resource_id: Callable to get resource_id (optional)
        success_callback: Callable to determine success and get details (optional)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_jwt_extended import get_jwt_identity
            from app.models.user import User
            
            user_id = None
            username = None
            resource_id = None
            success = True
            error_message = None
            details = None
            
            try:
                # Get user info
                try:
                    current_user_id = get_jwt_identity()
                    if current_user_id:
                        user_id = int(current_user_id)
                        user = User.query.get(user_id)
                        if user:
                            username = user.username
                except:
                    pass  # User may not be authenticated for some endpoints
                
                # Get resource ID if function provided
                if get_resource_id:
                    try:
                        resource_id = get_resource_id()
                    except:
                        pass
                
                # Call the original function
                result = f(*args, **kwargs)
                
                # Determine success and get details
                if success_callback:
                    try:
                        success_result = success_callback(result)
                        if isinstance(success_result, dict):
                            success = success_result.get('success', True)
                            details = success_result.get('details')
                        else:
                            success = bool(success_result)
                    except:
                        pass
                else:
                    # Default: check HTTP status code if result is a tuple
                    if isinstance(result, tuple) and len(result) >= 2:
                        status_code = result[1]
                        success = 200 <= status_code < 400
                
                # Log the action
                AuditService.log_action(
                    user_id=user_id,
                    username=username,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=success,
                    error_message=error_message,
                    details=details
                )
                
                return result
                
            except Exception as e:
                # Log failed action
                error_message = str(e)[:500] if str(e) else 'Unknown error'
                # Ensure no PHI in error message
                error_message = AuditService._sanitize_error_message(error_message)
                
                AuditService.log_action(
                    user_id=user_id,
                    username=username,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=False,
                    error_message=error_message
                )
                raise
        
        return decorated_function
    return decorator

