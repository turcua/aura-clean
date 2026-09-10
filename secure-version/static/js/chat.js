/**
 * Aura Financial Tracker - Secure Version
 * AI Advisor chat bubble + panel controller
 * Sprint 23: AI Advisor Foundation
 *
 * No user_id anywhere — every request relies on the session cookie. All
 * message content is rendered via textContent, never innerHTML —
 * vulnerable-version's equivalent renders it via innerHTML.
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
                fetch('/api/ai-advisor/clear', { method: 'POST' })
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

        fetch('/api/ai-advisor/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        })
            .then(r => r.json())
            .then(j => {
                pending.remove();
                if (j.success) {
                    if (j.message) appendMessage('assistant', j.message);
                    if (j.pending_actions && j.pending_actions.length) {
                        j.pending_actions.forEach(appendActionCard);
                    }
                } else {
                    appendMessage('assistant', j.message || 'Something went wrong. Please try again.');
                }
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
    fetch('/api/ai-advisor/history')
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
    const el = document.createElement('div');
    el.className = 'chat-message ' + (role === 'user' ? 'chat-message-user' : 'chat-message-assistant');
    el.textContent = content;
    list.appendChild(el);
    list.scrollTop = list.scrollHeight;
    return el;
}

function appendActionCard(action) {
    const list = document.getElementById('chatMessageList');
    if (!list) return;

    const card = document.createElement('div');
    card.className = 'chat-action-card' + (action.warning ? ' chat-action-card-warning' : '');

    const desc = document.createElement('div');
    desc.className = 'chat-action-desc';
    desc.textContent = action.description;
    card.appendChild(desc);

    if (action.warning) {
        const warning = document.createElement('div');
        warning.className = 'chat-action-warning';
        warning.textContent = '⚠️ ' + action.warning;
        card.appendChild(warning);
    }

    const buttons = document.createElement('div');
    buttons.className = 'chat-action-buttons';

    const confirmBtn = document.createElement('button');
    confirmBtn.type = 'button';
    confirmBtn.className = 'chat-action-confirm-btn';
    confirmBtn.textContent = 'Confirm';
    confirmBtn.addEventListener('click', () => resolveAction(action.id, true, card));
    buttons.appendChild(confirmBtn);

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'chat-action-cancel-btn';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.addEventListener('click', () => resolveAction(action.id, false, card));
    buttons.appendChild(cancelBtn);

    card.appendChild(buttons);
    list.appendChild(card);
    list.scrollTop = list.scrollHeight;
}

function resolveAction(actionId, confirm, card) {
    const buttons = card.querySelectorAll('button');
    buttons.forEach(b => b.disabled = true);

    fetch(`/api/ai-advisor/confirm-action/${actionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm }),
    })
        .then(r => r.json())
        .then(j => {
            card.remove();
            appendMessage('assistant', j.message || (confirm ? 'Action confirmed.' : 'Action cancelled.'));
        })
        .catch(() => {
            buttons.forEach(b => b.disabled = false);
        });
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
