USE aura_vulnerable;

-- notifications.message was VARCHAR(500) (Sprint 21) — a multi-finding AI
-- insight narration (Sprint 25) can legitimately exceed that. Widened to
-- TEXT, matching ai_conversations.content's precedent. Not a vulnerability
-- fix — this schema limit affected both versions identically, it just
-- hadn't been triggered on secure-version's test data yet.
ALTER TABLE notifications MODIFY message TEXT NOT NULL;

SELECT 'Vulnerable Sprint 25 schema updated successfully!' AS status;
