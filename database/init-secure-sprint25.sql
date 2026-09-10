USE aura_secure;

-- notifications.message was VARCHAR(500) (Sprint 21) — a multi-finding AI
-- insight narration (Sprint 25) can legitimately exceed that. Widened to
-- TEXT, matching ai_conversations.content's precedent.
ALTER TABLE notifications MODIFY message TEXT NOT NULL;

SELECT 'Secure Sprint 25 schema updated successfully!' AS status;
