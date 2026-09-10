-- Aura Financial Tracker - Secure Version
-- Sprint 57 (ENH-02, group 5): scheduler job health tracking for the admin
-- panel. Previously the 4 background jobs (scheduler.py) only print() to
-- console, and only when something actually happened (count > 0) — a job
-- silently crashing every hour left no record at all. One row per
-- execution, every execution (success, no-op, or error), not just the
-- "did something" ones.
CREATE TABLE IF NOT EXISTS scheduler_job_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(50) NOT NULL,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'error') NOT NULL,
    result_count INT DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    INDEX idx_job_id (job_id),
    INDEX idx_run_at (run_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
