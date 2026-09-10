"""
Aura Financial Tracker - Vulnerable Version
Notifications API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 21: In-App Notifications
"""

from flask import Blueprint, request, jsonify, current_app, session
from models.notification import Notification
from utils import flag_engine

api_notifications_bp = Blueprint('api_notifications', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_notifications_bp.route('/list', methods=['GET'])
def list_notifications():
    """
    VULNERABILITIES: No auth, IDOR — any user_id returns that user's
    notifications, SQL Injection via user_id (in the model)
    """
    try:
        user_id = request.args.get('user_id', '')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        notifications = Notification.get_visible_by_user(mysql, user_id)
        unread_count = Notification.get_unread_count(mysql, user_id)

        # Sprint 44 (VULN-073 flag): reading someone else's notifications
        # via the user_id param is the proof.
        attacker_id = session.get('user_id')
        if attacker_id and str(user_id) != str(attacker_id):
            flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-073')

        return jsonify({
            'success': True,
            'notifications': [_notification_to_dict(n) for n in notifications],
            'unread_count': unread_count,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
def mark_read(notification_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on notification_id"""
    try:
        mysql = get_mysql()
        Notification.mark_read(mysql, notification_id)
        return jsonify({'success': True, 'message': 'Notification marked as read'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_notifications_bp.route('/<int:notification_id>/dismiss', methods=['POST'])
def dismiss(notification_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on notification_id"""
    try:
        mysql = get_mysql()
        Notification.dismiss(mysql, notification_id)
        return jsonify({'success': True, 'message': 'Notification dismissed'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_notifications_bp.route('/mark-all-read', methods=['POST'])
def mark_all_read():
    """VULNERABILITY: No auth, IDOR — user_id from request body, can mark another user's notifications"""
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        Notification.mark_all_read(mysql, user_id)
        return jsonify({'success': True, 'message': 'All notifications marked as read'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_notifications_bp.route('/delete-all', methods=['POST'])
def delete_all():
    """VULNERABILITY: No auth, IDOR — user_id from request body, can delete another user's notifications entirely"""
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        Notification.delete_all(mysql, user_id)
        return jsonify({'success': True, 'message': 'All notifications deleted'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _notification_to_dict(n):
    return {
        'id': n.id,
        'user_id': n.user_id,  # VULN: Exposing user_id
        'type': n.type,
        'title': n.title,
        'message': n.message,
        'is_read': n.is_read,
        'created_at': str(n.created_at) if n.created_at else None,
    }
