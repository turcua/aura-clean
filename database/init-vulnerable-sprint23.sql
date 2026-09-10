USE aura_vulnerable;

-- Same shape as secure-version — the vulnerability here isn't in the schema,
-- it's in how the app queries/authorizes access to these rows (see
-- models/ai_conversation.py and routes/api/ai_advisor.py: f-string SQL,
-- user_id from request, no ownership check — VULN-075).
CREATE TABLE IF NOT EXISTS ai_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_created (user_id, created_at)
);

SELECT 'Vulnerable Sprint 23 schema created successfully!' AS status;
