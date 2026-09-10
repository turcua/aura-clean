USE aura_secure;

-- Sprint 52 (ENH-03): password reset via emailed token. reset_token is a
-- cryptographically random value (secrets.token_urlsafe), single-use —
-- cleared immediately after a successful reset — and time-limited via
-- reset_token_expires (PASSWORD_RESET_TOKEN_EXPIRY_MINUTES in config.py).
ALTER TABLE users
    ADD COLUMN reset_token VARCHAR(255) NULL,
    ADD COLUMN reset_token_expires TIMESTAMP NULL;

SELECT 'Secure Sprint 52 schema (users password-reset columns) created successfully!' AS status;
