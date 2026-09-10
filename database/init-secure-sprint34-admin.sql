USE aura_secure;

-- Sprint 34 (ad-hoc addition, not originally scoped for this sprint): adds a
-- minimal is_admin flag so a real, auth-gated admin panel can exist and be
-- validated in secure-version. Mirrors vulnerable-version's /admin route
-- conceptually, but properly gated (unlike VULN-002's zero auth check) and
-- never exposes password hashes.
ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;

SELECT 'Secure Sprint 34 (admin) schema updated successfully!' AS status;
