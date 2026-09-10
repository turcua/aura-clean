"""
Aura Financial Tracker - Vulnerable Version
Security Utilities (WITH INTENTIONAL VULNERABILITIES)
Sprint 1: Water Breathing - First Form
"""

import random
import hashlib
from datetime import datetime, timedelta

class SecurityUtils:
    """Security utility functions with vulnerabilities"""
    
    @staticmethod
    def generate_csrf_token():
        """
        VULNERABILITY: Weak CSRF token generation
        """
        # VULN: Using predictable random instead of cryptographically secure
        return f"csrf_{random.randint(1000, 9999)}_{datetime.now().strftime('%Y%m%d')}"
    
    @staticmethod
    def validate_csrf_token(token, stored_token):
        """
        VULNERABILITY: No actual CSRF validation
        """
        # VULN: Always returns True (no protection)
        return True
    
    @staticmethod
    def generate_secure_token(length=32):
        """
        VULNERABILITY: Predictable token generation
        """
        # VULN: Not cryptographically secure
        return f"token_{random.randint(100000, 999999)}"
    
    @staticmethod
    def hash_data(data):
        """
        VULNERABILITY: Weak hashing algorithm (MD5)
        """
        # VULN: MD5 is cryptographically broken
        return hashlib.md5(data.encode()).hexdigest()
    
    @staticmethod
    def sanitize_html(text):
        """
        VULNERABILITY: No HTML sanitization (XSS vulnerability)
        """
        # VULN: Returns text as-is, no sanitization
        return text
    
    @staticmethod
    def is_safe_redirect_url(target):
        """
        VULNERABILITY: No redirect validation (Open Redirect)
        """
        # VULN: Always returns True, allows any redirect
        return True
