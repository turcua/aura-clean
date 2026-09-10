USE aura_vulnerable;

-- Real flag storage for the CTF mechanism (Sprint 43). Note this table's
-- own read/write API (routes/api/scoreboard.py mark/unmark/progress) is
-- intentionally vulnerable per VULN-082 — but flag_value itself is only
-- ever written by utils/flag_engine.py (server-side, triggered by a
-- vulnerability's own leak actually firing), never accepted directly from
-- a request body anywhere.
ALTER TABLE scoreboard_progress ADD COLUMN flag_value VARCHAR(64) NULL;

-- Global, organizer-controlled mode toggle (Sprint 43 scope decision:
-- instance-wide, not per-user). 'casual' hides flag values in responses;
-- 'ctf' reveals them. Exploiting a vulnerability always marks it solved
-- either way — this only controls whether the flag text is shown.
CREATE TABLE IF NOT EXISTS ctf_settings (
    setting_key VARCHAR(50) PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL
);

INSERT IGNORE INTO ctf_settings (setting_key, setting_value) VALUES ('mode', 'casual');

SELECT 'Vulnerable Sprint 43 schema created successfully!' AS status;
