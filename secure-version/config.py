"""
Aura Financial Tracker - Secure Version
Configuration File
Sprint 1: Water Breathing - First Form
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class with secure defaults"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secure-secret-key-change-in-production-xyz123'
    
    # Database Configuration
    MYSQL_HOST = os.environ.get('DATABASE_HOST', 'mysql-secure')
    MYSQL_PORT = int(os.environ.get('DATABASE_PORT', 3306))
    MYSQL_USER = os.environ.get('DATABASE_USER', 'aura_user')
    MYSQL_PASSWORD = os.environ.get('DATABASE_PASSWORD', 'SecureUserPass123!')
    MYSQL_DB = os.environ.get('DATABASE_NAME', 'aura_secure')
    
    # Session Configuration (Secure)
    # True by default (production-safe); disabled only in local dev (FLASK_ENV=development)
    # since browsers refuse to store/send a Secure-flagged cookie over plain HTTP.
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') != 'development'
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # Session expires after 2 hours
    
    # Security Headers
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable caching for security

    # Upload limits (Sprint 14) — caps request body size globally, so the CSV
    # import endpoint can never be sent an unbounded file (vulnerable-version
    # has no file size limit at all on /api/export/import/csv)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    
    # Rate Limiting
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_TIMEOUT_MINUTES = 15
    
    # Password Requirements
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL_CHARS = True
    
    # AI Advisor (Sprint 23) — Groq API
    # No hardcoded fallback for the key itself (unlike DATABASE_PASSWORD/
    # SECRET_KEY above) — this is a real external credential, not a lab
    # value, so an unset key must fail loudly rather than silently run with
    # a placeholder. GROQ_MODEL isn't a secret, so it does get a default.
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')

    # Password Reset (Sprint 52, ENH-03) — real SMTP delivery. Same
    # GROQ_API_KEY precedent: MAIL_USERNAME/MAIL_PASSWORD are real external
    # credentials with no hardcoded fallback, must fail loudly if unset
    # rather than silently run with a placeholder. MAIL_SERVER/MAIL_PORT
    # aren't secrets, so they do get sensible defaults (Gmail SMTP).
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME
    PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 60

    # 2FA (Sprint 52, ENH-04) — TOTP, RFC 6238. No external credential
    # involved (secrets are generated per-user, stored in the DB), so
    # nothing here needs the GROQ_API_KEY-style "no fallback" treatment.
    TOTP_ISSUER_NAME = "Aura (Secure)"

    # Application Settings
    APP_NAME = "Aura Financial Tracker - Secure"
    APP_VERSION = "1.0.0"
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
