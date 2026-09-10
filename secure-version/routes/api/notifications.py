"""
Aura Financial Tracker - Secure Version
Notifications API Routes
Sprint 21: In-App Notifications

Security properties (contrast with vulnerable-version/routes/api/notifications.py):
- Every route requires @api_login_required; user_id always comes from session
- notification_id ownership enforced at the model layer (id = %s AND user_id = %s)
"""

from flask import Blueprint, jsonify, session, current_app
from models.notification import Notification
from routes.main import api_login_required

api_notifications_bp = Blueprint('api_notifications', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_notifications_bp.route('/list', methods=['GET'])
@api_login_required
def list_notifications():
    mysql = get_mysql()
    user_id = session['user_id']
    notifications = Notification.get_visible_by_user(mysql, user_id)
    unread_count = Notification.get_unread_count(mysql, user_id)
    return jsonify({
        'success': True,
        'notifications': [_notification_to_dict(n) for n in notifications],
        'unread_count': unread_count,
    }), 200


@api_notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@api_login_required
def mark_read(notification_id):
    mysql = get_mysql()
    success = Notification.mark_read(mysql, notification_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': 'Notification marked as read'}), 200
    return jsonify({'success': False, 'message': "Notification not found or you don't have permission"}), 404


@api_notifications_bp.route('/<int:notification_id>/dismiss', methods=['POST'])
@api_login_required
def dismiss(notification_id):
    mysql = get_mysql()
    success = Notification.dismiss(mysql, notification_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': 'Notification dismissed'}), 200
    return jsonify({'success': False, 'message': "Notification not found or you don't have permission"}), 404


@api_notifications_bp.route('/mark-all-read', methods=['POST'])
@api_login_required
def mark_all_read():
    mysql = get_mysql()
    Notification.mark_all_read(mysql, session['user_id'])
    return jsonify({'success': True, 'message': 'All notifications marked as read'}), 200


@api_notifications_bp.route('/delete-all', methods=['POST'])
@api_login_required
def delete_all():
    mysql = get_mysql()
    Notification.delete_all(mysql, session['user_id'])
    return jsonify({'success': True, 'message': 'All notifications deleted'}), 200


def _notification_to_dict(n):
    return {
        'id': n.id,
        'type': n.type,
        'title': n.title,
        'message': n.message,
        'is_read': n.is_read,
        'created_at': str(n.created_at) if n.created_at else None,
    }
