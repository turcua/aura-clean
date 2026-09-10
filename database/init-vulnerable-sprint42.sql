USE aura_vulnerable;

-- Same shape as secure-version would be — the vulnerability here isn't in
-- the schema, it's in how the app queries/authorizes access to these rows
-- (see routes/api/scoreboard.py: user_id taken from the request body/query
-- string, no ownership check — VULN-082). Sprint 42 (Release 9).
CREATE TABLE IF NOT EXISTS scoreboard_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    vuln_id VARCHAR(20) NOT NULL,
    found_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source ENUM('self_report', 'flag') NOT NULL DEFAULT 'self_report',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_vuln (user_id, vuln_id)
);

SELECT 'Vulnerable Sprint 42 schema created successfully!' AS status;
