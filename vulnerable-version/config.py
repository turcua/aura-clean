"""
Aura Financial Tracker - Vulnerable Version
Configuration File (WITH INTENTIONAL VULNERABILITIES)
Sprint 1: Water Breathing - First Form
"""

import os
from datetime import timedelta

class Config:
    """Configuration class with intentional security weaknesses"""
    
    # Flask Configuration
    # VULNERABILITY: Weak, predictable secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'weak-secret-123'
    
    # Database Configuration
    MYSQL_HOST = os.environ.get('DATABASE_HOST', 'mysql-vulnerable')
    MYSQL_PORT = int(os.environ.get('DATABASE_PORT', 3306))
    MYSQL_USER = os.environ.get('DATABASE_USER', 'aura_user')
    MYSQL_PASSWORD = os.environ.get('DATABASE_PASSWORD', 'VulnUserPass123!')
    MYSQL_DB = os.environ.get('DATABASE_NAME', 'aura_vulnerable')
    
    # Session Configuration (Vulnerable)
    # VULNERABILITY: No secure cookie flags
    SESSION_COOKIE_SECURE = False  # VULN: Sends cookie over HTTP
    SESSION_COOKIE_HTTPONLY = False  # VULN: JavaScript can access session cookie (XSS)
    SESSION_COOKIE_SAMESITE = None  # VULN: No CSRF protection
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)  # VULN: Session never expires
    
    # Security Headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # VULN: Long caching
    
    # Rate Limiting
    # VULNERABILITY: No rate limiting
    MAX_LOGIN_ATTEMPTS = 999999  # VULN: Unlimited login attempts (brute force)
    LOGIN_TIMEOUT_MINUTES = 0
    
    # Password Requirements
    # VULNERABILITY: Weak password requirements
    MIN_PASSWORD_LENGTH = 1  # VULN: Allows single character passwords
    REQUIRE_UPPERCASE = False
    REQUIRE_LOWERCASE = False
    REQUIRE_DIGITS = False
    REQUIRE_SPECIAL_CHARS = False
    
    # AI Advisor (Sprint 23) — Groq API
    # No hardcoded fallback for the key itself — a real external credential.
    # VULNERABILITY: reachable via the extended /auth/debug/session endpoint
    # (see routes/auth.py) — VULN-076, insecure API key storage.
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')

    # Password Reset (Sprint 52, ENH-03) — real SMTP delivery, separate
    # credentials from secure-version (same GROQ_API_KEY precedent).
    # VULNERABILITY: the token VALUE itself is weak/predictable — see
    # models/user.py's generate_reset_token() — not this config.
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME
    PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 60  # VULN: not actually enforced — see routes/auth.py

    # 2FA (Sprint 52, ENH-04) — TOTP.
    # VULNERABILITY: no rate limiting on verification attempts (routes/auth.py),
    # matching this file's existing MAX_LOGIN_ATTEMPTS = 999999 theme — a
    # 6-digit TOTP code becomes brute-forceable.
    TOTP_ISSUER_NAME = "Aura (Vulnerable)"

    # Application Settings
    APP_NAME = "Aura Financial Tracker - Vulnerable"
    APP_VERSION = "1.0.0-VULN"
    DEBUG = True  # VULN: Debug mode always on (information disclosure)
