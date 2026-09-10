USE aura_secure;

-- Sprint 26: Excessive Agency. Solis proposing a tool call never executes
-- anything directly — it's stored here as a pending row, and only
-- POST /api/ai-advisor/confirm-action (after independently re-validating
-- every parameter server-side) can turn it into a real write.
-- vulnerable-version/ has no equivalent table — it executes immediately,
-- with no pending state at all (VULN-079).
CREATE TABLE IF NOT EXISTS ai_pending_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_params JSON NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_status (user_id, status)
);

SELECT 'Secure Sprint 26 schema created successfully!' AS status;
