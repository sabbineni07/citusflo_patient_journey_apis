from app import db
from datetime import datetime
import json

class WebAuthnCredential(db.Model):
    """Model for storing WebAuthn credentials"""
    __tablename__ = 'webauthn_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    credential_id = db.Column(db.Text, unique=True, nullable=False)  # Base64url encoded
    public_key = db.Column(db.Text, nullable=False)  # CBOR encoded public key
    counter = db.Column(db.Integer, default=0, nullable=False)
    aaguid = db.Column(db.String(36), nullable=True)  # Authenticator Attestation GUID
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship with user
    user = db.relationship('User', backref='webauthn_credentials', lazy=True)
    
    def to_dict(self):
        """Convert credential to dictionary"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'credential_id': self.credential_id,
            'counter': self.counter,
            'aaguid': self.aaguid,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }
    
    def __repr__(self):
        return f'<WebAuthnCredential {self.credential_id[:20]}...>'



