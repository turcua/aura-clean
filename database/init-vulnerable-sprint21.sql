USE aura_vulnerable;

-- VULNERABILITY: no UNIQUE(user_id, dedupe_key) — unlike secure-version,
-- duplicate-safe notification generation isn't enforced at the DB level,
-- only (imperfectly) checked in application code. Consistent with this
-- version's established pattern of skipping DB-level integrity
-- enforcement (see VULN-065's history in docs/vulnerability-matrix.md).
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type VARCHAR(30) NOT NULL,
    title VARCHAR(150) NOT NULL,
    message VARCHAR(500) NOT NULL,
    dedupe_key VARCHAR(255) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    dismissed_at TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

SELECT 'Vulnerable Sprint 21 schema created successfully!' AS status;
