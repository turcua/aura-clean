USE aura_vulnerable;

-- Sprint 43 follow-up (found via real user testing, 2026-08-08): the popup's
-- "already shown you this" tracking was client-side (localStorage), which
-- is scoped to the browser, not the account — any fresh incognito window
-- or different browser has no memory of what it already announced, so
-- every legitimately-earned flag re-announces itself. Moved server-side,
-- tied to the account, so it works consistently regardless of browser.
ALTER TABLE scoreboard_progress ADD COLUMN notified_at DATETIME NULL DEFAULT NULL;

SELECT 'Vulnerable Sprint 43 notify-tracking hotfix applied successfully!' AS status;
