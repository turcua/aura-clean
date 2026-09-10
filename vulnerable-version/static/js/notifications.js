/**
 * Aura Financial Tracker - Vulnerable Version
 * Notification bell + panel controller (WITH INTENTIONAL VULNERABILITIES)
 * Sprint 21: In-App Notifications
 *
 * VULNERABILITY: user_id read from window.CURRENT_USER_ID and sent on
 * every request — trivially tampered with via DevTools before the app
 * ever loaded, or by calling the API directly with a different value
 * (VULN-073, IDOR).
 * VULNERABILITY: notification title/message rendered via innerHTML
 * (VULN-074, Stored XSS) — these strings can contain a category name or a
 * recurring-transaction description, both already user-controlled data
 * elsewhere in this app.
 */

'use strict';

const NOTIFICATION_POLL_INTERVAL_MS = 60000;

document.addEventListener('DOMContentLoaded', () => {
    const bellBtn = document.getElementById('notificationBellBtn');
    const panel = document.getElementById('notificationPanel');
    const markAllBtn = document.getElementById('markAllReadBtn');
    const deleteAllBtn = document.getElementById('deleteAllBtn');
    if (!bellBtn || !panel) return;

    bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = panel.style.display !== 'none';
        panel.style.display = isOpen ? 'none' : '';
        if (!isOpen) loadNotifications();
    });

    document.addEventListener('click', (e) => {
        if (!panel.contains(e.target) && e.target !== bellBtn) {
            panel.style.display = 'none';
        }
    });

    markAllBtn.addEventListener('click', () => {
        fetch('/api/notifications/mark-all-read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: window.CURRENT_USER_ID })
        })
            .then(r => r.json())
            .then(j => { if (j.success) loadNotifications(); });
    });

    deleteAllBtn.addEventListener('click', () => {
        Swal.fire({
            title: 'Delete all notifications?',
            text: 'This permanently removes every notification and cannot be undone.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Delete all',
            cancelButtonText: 'Cancel',
            confirmButtonColor: '#ef4444',
        }).then(result => {
            if (!result.isConfirmed) return;
            // VULN: user_id trusted as-is, no ownership check server-side (VULN-073)
            fetch('/api/notifications/delete-all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: window.CURRENT_USER_ID })
            })
                .then(r => r.json())
                .then(j => { if (j.success) loadNotifications(); });
        });
    });

    loadNotifications();
    setInterval(loadNotifications, NOTIFICATION_POLL_INTERVAL_MS);
});

function loadNotifications() {
    // VULN: user_id in the query string, trivially tampered with (IDOR)
    fetch(`/api/notifications/list?user_id=${window.CURRENT_USER_ID}`)
        .then(r => r.json())
        .then(j => {
            if (!j.success) return;
            renderBadge(j.unread_count);
            renderList(j.notifications);
        })
        .catch(() => {});
}

function renderBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : String(count);
        badge.style.display = '';
    } else {
        badge.style.display = 'none';
    }
}

function renderList(notifications) {
    const list = document.getElementById('notificationList');
    if (!list) return;

    if (!notifications.length) {
        list.innerHTML = `<div class="notification-empty">No notifications</div>`;
        return;
    }

    // VULN: title/message rendered via innerHTML — Stored XSS (VULN-074)
    list.innerHTML = notifications.map(n => `
        <div class="notification-item ${n.is_read ? '' : 'is-unread'}" data-id="${n.id}" onclick="markRead(${n.id})">
            <div class="notification-item-body">
                <div class="notification-item-title">${n.title}</div>
                <div class="notification-item-message">${n.message}</div>
                <div class="notification-item-time">${formatRelativeTime(n.created_at)}</div>
            </div>
            <button type="button" class="notification-item-dismiss" title="Dismiss" onclick="event.stopPropagation(); dismissNotification(${n.id})">&times;</button>
        </div>`).join('');
}

function markRead(id) {
    fetch(`/api/notifications/${id}/read`, { method: 'POST' })
        .then(r => r.json())
        .then(j => { if (j.success) loadNotifications(); });
}

function dismissNotification(id) {
    fetch(`/api/notifications/${id}/dismiss`, { method: 'POST' })
        .then(r => r.json())
        .then(j => { if (j.success) loadNotifications(); });
}

function formatRelativeTime(isoString) {
    if (!isoString) return '';
    const then = new Date(isoString.replace(' ', 'T'));
    const diffMs = Date.now() - then.getTime();
    const diffMin = Math.round(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.round(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.round(diffHr / 24);
    return `${diffDay}d ago`;
}
