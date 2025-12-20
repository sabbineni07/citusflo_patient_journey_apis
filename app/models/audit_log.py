"""
Audit log model for HIPAA compliance
Tracks all access to and modifications of Protected Health Information (PHI)
"""
from app import db
from datetime import datetime
from enum import Enum

class AuditActionType(Enum):
    """Types of audit actions"""
    LOGIN = 'login'
    LOGOUT = 'logout'
    LOGIN_FAILED = 'login_failed'
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'
    EXPORT = 'export'
    VIEW = 'view'
    ACCESS_DENIED = 'access_denied'
    PASSWORD_CHANGE = 'password_change'
    USER_CREATED = 'user_created'
    USER_UPDATED = 'user_updated'
    USER_DELETED = 'user_deleted'

class AuditResourceType(Enum):
    """Types of resources being audited"""
    PATIENT = 'patient'
    PATIENT_FORM = 'patient_form'
    USER = 'user'
    FACILITY = 'facility'
    HOME_HEALTH = 'home_health'
    HOSPITAL = 'hospital'
    AUTHENTICATION = 'authentication'
    SYSTEM = 'system'

class AuditLog(db.Model):
    """Model for storing audit logs of PHI access and modifications"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    username = db.Column(db.String(80), nullable=True, index=True)  # Store username for historical reference
    action = db.Column(db.String(50), nullable=False, index=True)  # AuditActionType as string
    resource_type = db.Column(db.String(50), nullable=False, index=True)  # AuditResourceType as string
    resource_id = db.Column(db.String(100), nullable=True, index=True)  # ID of the resource (patient_id, user_id, etc.)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.Text, nullable=True)  # Browser/client user agent
    success = db.Column(db.Boolean, default=True, nullable=False, index=True)  # Whether action was successful
    error_message = db.Column(db.Text, nullable=True)  # Error message if failed (no PHI)
    details = db.Column(db.JSON, nullable=True)  # Additional context (fields changed, etc.) - NO PHI
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship with user (optional - user may be deleted)
    user = db.relationship('User', foreign_keys=[user_id], lazy=True)
    
    def to_dict(self):
        """Convert audit log to dictionary (for API responses)"""
        return {
            'id': self.id,
            'userId': self.user_id,
            'username': self.username,
            'action': self.action,
            'resourceType': self.resource_type,
            'resourceId': self.resource_id,
            'ipAddress': self.ip_address,
            'userAgent': self.user_agent,
            'success': self.success,
            'errorMessage': self.error_message,
            'details': self.details,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<AuditLog {self.id}: {self.action} {self.resource_type}/{self.resource_id} by user {self.user_id}>'


