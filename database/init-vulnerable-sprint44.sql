USE aura_vulnerable;

-- Sprint 44 — the "vault" flag-embedding pattern: a table that isn't
-- reachable through any normal app feature, only through a UNION-based
-- SQL injection that specifically targets it by name (e.g. discovered via
-- information_schema enumeration, or just guessed). The flag itself isn't
-- stored here — flags are generated per-user by utils/flag_engine.py the
-- moment genuine exploitation is detected server-side (see
-- routes/api/export.py's import_csv, VULN-043) — this table exists purely
-- as the target a hacker has to find and reference successfully.
CREATE TABLE IF NOT EXISTS ctf_vault (
    id INT AUTO_INCREMENT PRIMARY KEY,
    note VARCHAR(255) NOT NULL DEFAULT 'nice find'
);

INSERT INTO ctf_vault (note) SELECT 'nice find' WHERE NOT EXISTS (SELECT 1 FROM ctf_vault);

SELECT 'Vulnerable Sprint 44 schema created successfully!' AS status;
