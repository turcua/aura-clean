-- Aura Financial Tracker - Secure Version
-- Sprint 57 (ENH-02, group 6): "View As" / impersonate a user. Audit log —
-- every impersonation, who did it, who was targeted, when it started and
-- (if properly ended via "Return to Admin") when it ended. ended_at stays
-- NULL if the admin's browser tab/session was simply closed/expired
-- instead of explicitly ending it — same as any session timing out, not a
-- bug, but worth being able to see in the admin panel's audit view.
CREATE TABLE IF NOT EXISTS impersonation_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    target_user_id INT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (target_user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_admin_id (admin_id),
    INDEX idx_target_user_id (target_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
