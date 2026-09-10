USE aura_secure;

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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_dedupe UNIQUE (user_id, dedupe_key)
);

SELECT 'Secure Sprint 21 schema created successfully!' AS status;
