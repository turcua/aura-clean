/**
 * Aura Financial Tracker - Vulnerable Version
 * AI Advisor chat bubble + panel controller (WITH INTENTIONAL VULNERABILITIES)
 * Sprint 23: AI Advisor Foundation
 *
 * VULNERABILITY: user_id read from window.CURRENT_USER_ID and sent on every
 * request — trivially tampered with (VULN-075, IDOR).
 * VULNERABILITY: message content rendered via innerHTML, not textContent —
 * both the user's own message and the AI's response (which can echo back
 * attacker-controlled content) are unescaped.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const bubbleBtn = document.getElementById('chatBubbleBtn');
    const panel = document.getElementById('chatPanel');
    const form = document.getElementById('chatInputForm');
    const input = document.getElementById('chatInput');
    const clearBtn = document.getElementById('chatClearBtn');
    if (!bubbleBtn || !panel || !form || !input) return;

    let historyLoaded = false;

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            Swal.fire({
                title: 'Clear conversation?',
                text: 'This permanently deletes your entire chat history with Solis and cannot be undone.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Clear',
                cancelButtonText: 'Cancel',
                confirmButtonColor: '#ef4444',
            }).then(result => {
                if (!result.isConfirmed) return;
                // VULN: user_id trusted as-is, no ownership check server-side (VULN-075)
                fetch('/api/ai-advisor/clear', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: window.CURRENT_USER_ID }),
                })
                    .then(r => r.json())
                    .then(j => {
                        if (!j.success) return;
                        const list = document.getElementById('chatMessageList');
                        if (list) list.innerHTML = '';
                        appendMessage('assistant', "Hi, I'm Solis. Ask me anything about your finances — spending, budgets, or savings goals.");
                    });
            });
        });
    }

    bubbleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = panel.style.display !== 'none';
        panel.style.display = isOpen ? 'none' : '';
        if (!isOpen && !historyLoaded) {
            historyLoaded = true;
            loadHistory();
        }
    });

    document.addEventListener('click', (e) => {
        if (!panel.contains(e.target) && e.target !== bubbleBtn) {
            panel.style.display = 'none';
        }
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        appendMessage('user', message);
        input.value = '';
        setInputDisabled(true);
        const pending = appendPending();

        // VULN: user_id sent from a client-controlled global (IDOR)
        fetch('/api/ai-advisor/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: window.CURRENT_USER_ID, message }),
        })
            .then(r => r.json())
            .then(j => {
                pending.remove();
                appendMessage('assistant', j.message || 'Something went wrong. Please try again.');
            })
            .catch(() => {
                pending.remove();
                appendMessage('assistant', 'Something went wrong. Please try again.');
            })
            .finally(() => setInputDisabled(false));
    });
});

function setInputDisabled(disabled) {
    const input = document.getElementById('chatInput');
    const btn = document.querySelector('.chat-send-btn');
    if (input) input.disabled = disabled;
    if (btn) btn.disabled = disabled;
}

function loadHistory() {
    // VULN: user_id in the query string, trivially tampered with (IDOR)
    fetch(`/api/ai-advisor/history?user_id=${window.CURRENT_USER_ID}`)
        .then(r => r.json())
        .then(j => {
            if (!j.success) return;
            const list = document.getElementById('chatMessageList');
            if (!list) return;
            list.innerHTML = '';
            if (!j.messages.length) {
                appendMessage('assistant', "Hi, I'm Solis. Ask me anything about your finances — spending, budgets, or savings goals.");
                return;
            }
            j.messages.forEach(m => appendMessage(m.role, m.content));
        })
        .catch(() => {});
}

function appendMessage(role, content) {
    const list = document.getElementById('chatMessageList');
    if (!list) return;
    const cls = role === 'user' ? 'chat-message-user' : 'chat-message-assistant';
    // VULN: innerHTML — Stored/Reflected XSS via message content
    const el = document.createElement('div');
    el.className = 'chat-message ' + cls;
    el.innerHTML = content;
    list.appendChild(el);
    list.scrollTop = list.scrollHeight;
    return el;
}

function appendPending() {
    const list = document.getElementById('chatMessageList');
    const el = document.createElement('div');
    el.className = 'chat-message chat-message-pending';
    el.textContent = 'Thinking…';
    list.appendChild(el);
    list.scrollTop = list.scrollHeight;
    return el;
}
