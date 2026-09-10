/**
 * Aura Financial Tracker - Secure Version
 * Notification bell + panel controller
 * Sprint 21: In-App Notifications
 *
 * No user_id anywhere — every request relies on the session cookie. All
 * notification content (title/message) is rendered via textContent, never
 * innerHTML — vulnerable-version's equivalent renders it via innerHTML
 * (Stored XSS, VULN-074), since category names / recurring-transaction
 * descriptions embedded in these messages are user-controlled elsewhere
 * in the app.
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
        fetch('/api/notifications/mark-all-read', { method: 'POST' })
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
            fetch('/api/notifications/delete-all', { method: 'POST' })
                .then(r => r.json())
                .then(j => { if (j.success) loadNotifications(); });
        });
    });

    loadNotifications();
    setInterval(loadNotifications, NOTIFICATION_POLL_INTERVAL_MS);
});

function loadNotifications() {
    fetch('/api/notifications/list')
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
    list.innerHTML = '';

    if (!notifications.length) {
        const empty = document.createElement('div');
        empty.className = 'notification-empty';
        empty.textContent = 'No notifications';
        list.appendChild(empty);
        return;
    }

    notifications.forEach(n => list.appendChild(buildNotificationItem(n)));
}

function buildNotificationItem(n) {
    const item = document.createElement('div');
    item.className = 'notification-item' + (n.is_read ? '' : ' is-unread');
    item.dataset.id = n.id;

    const body = document.createElement('div');
    body.className = 'notification-item-body';

    const title = document.createElement('div');
    title.className = 'notification-item-title';
    title.textContent = n.title;
    body.appendChild(title);

    const message = document.createElement('div');
    message.className = 'notification-item-message';
    message.textContent = n.message;
    body.appendChild(message);

    const time = document.createElement('div');
    time.className = 'notification-item-time';
    time.textContent = formatRelativeTime(n.created_at);
    body.appendChild(time);

    item.appendChild(body);

    const dismissBtn = document.createElement('button');
    dismissBtn.type = 'button';
    dismissBtn.className = 'notification-item-dismiss';
    dismissBtn.title = 'Dismiss';
    dismissBtn.textContent = '×';
    dismissBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fetch(`/api/notifications/${n.id}/dismiss`, { method: 'POST' })
            .then(r => r.json())
            .then(j => { if (j.success) loadNotifications(); });
    });
    item.appendChild(dismissBtn);

    if (!n.is_read) {
        item.addEventListener('click', () => {
            fetch(`/api/notifications/${n.id}/read`, { method: 'POST' })
                .then(r => r.json())
                .then(j => { if (j.success) loadNotifications(); });
        });
    }

    return item;
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
