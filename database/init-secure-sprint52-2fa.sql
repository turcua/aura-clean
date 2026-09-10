USE aura_secure;

-- Sprint 52 (ENH-04): TOTP-based 2FA (RFC 6238). totp_secret is generated
-- per-user at setup time (pyotp.random_base32()) and only takes effect once
-- totp_enabled is confirmed TRUE after a successful verify-setup code —
-- setting a secret alone doesn't gate login.
ALTER TABLE users
    ADD COLUMN totp_secret VARCHAR(32) NULL,
    ADD COLUMN totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;

SELECT 'Secure Sprint 52 schema (users 2FA columns) created successfully!' AS status;
