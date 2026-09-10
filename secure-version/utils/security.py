"""
Aura Financial Tracker - Secure Version
Security Utilities
Sprint 1: Water Breathing - First Form
"""

import secrets
import hashlib
from datetime import datetime, timedelta

class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def generate_csrf_token():
        """Generate a CSRF token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_csrf_token(token, stored_token):
        """Validate CSRF token"""
        return secrets.compare_digest(token, stored_token)
    
    @staticmethod
    def generate_secure_token(length=32):
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_data(data):
        """Hash data using SHA-256"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def sanitize_html(text):
        """Sanitize HTML to prevent XSS"""
        if not text:
            return ""
        
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '&': '&amp;',
            '/': '&#x2F;'
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text
    
    @staticmethod
    def is_safe_redirect_url(target):
        """Check if redirect URL is safe (prevent open redirect)"""
        if not target:
            return False
        
        # Only allow relative URLs
        if target.startswith('/') and not target.startswith('//'):
            return True
        
        return False
