"""
Aura Financial Tracker - Secure Version
Dashboards API Routes
Sprint 14: Export/Import + Reports + Multi-Dashboard System

Security properties (contrast with vulnerable-version/routes/api/dashboards.py):
- Every route requires @api_login_required — vulnerable's routes have no
  auth check at all
- user_id always comes from session, never from the request body/query
  string — vulnerable's create_dashboard()/list_dashboards() take user_id
  from the request (mass assignment / IDOR)
- Every dashboard_id / widget_id is ownership-checked at the model layer
  (JOIN back to dashboards.user_id for widgets) — vulnerable has no
  ownership check anywhere in this file
- widget_type is validated against a whitelist before being attached
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.dashboard import Dashboard
from models.dashboard_widget import DashboardWidget, _UNSET
from routes.main import api_login_required

api_dashboards_bp = Blueprint('api_dashboards', __name__)


def get_mysql():
    return current_app.extensions['mysql']


# ── Dashboards ───────────────────────────────────────────────────────────────

@api_dashboards_bp.route('/list', methods=['GET'])
@api_login_required
def list_dashboards():
    """Returns all dashboards for the session user, auto-seeding 4 defaults if none exist."""
    try:
        mysql = get_mysql()
        user_id = session['user_id']
        dashboards = Dashboard.get_all_by_user(mysql, user_id)

        if not dashboards:
            Dashboard.create_defaults_for_user(mysql, user_id)
            dashboards = Dashboard.get_all_by_user(mysql, user_id)

        return jsonify({'success': True, 'dashboards': [_dashboard_to_dict(d) for d in dashboards]}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/activate', methods=['POST'])
@api_login_required
def activate_dashboard(dashboard_id):
    mysql = get_mysql()
    success = Dashboard.set_active(mysql, session['user_id'], dashboard_id)
    if success:
        return jsonify({'success': True, 'message': 'Dashboard activated'}), 200
    return jsonify({'success': False, 'message': 'Dashboard not found or you don\'t have permission'}), 404


@api_dashboards_bp.route('/create', methods=['POST'])
@api_login_required
def create_dashboard():
    try:
        data = request.get_json() if request.is_json else request.form
        name = (data.get('name') or '').strip()
        description = (data.get('description') or '').strip()

        if not name:
            return jsonify({'success': False, 'message': 'name is required'}), 400
        if len(name) > 100:
            return jsonify({'success': False, 'message': 'name is too long (max 100 characters)'}), 400
        if len(description) > 255:
            return jsonify({'success': False, 'message': 'description is too long (max 255 characters)'}), 400

        mysql = get_mysql()
        user_id = session['user_id']
        success, message, dashboard_id = Dashboard.create(mysql, user_id, name, description)

        if success:
            dash = Dashboard.get_by_id(mysql, dashboard_id, user_id)
            return jsonify({'success': True, 'dashboard': _dashboard_to_dict(dash)}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/update', methods=['POST', 'PUT'])
@api_login_required
def update_dashboard(dashboard_id):
    try:
        data = request.get_json() if request.is_json else request.form
        name = data.get('name')
        if name is not None:
            name = name.strip() or None
            if name and len(name) > 100:
                return jsonify({'success': False, 'message': 'name is too long (max 100 characters)'}), 400
        description = data.get('description')
        if description is not None:
            description = description.strip()
            if len(description) > 255:
                return jsonify({'success': False, 'message': 'description is too long (max 255 characters)'}), 400

        mysql = get_mysql()
        success, message = Dashboard.update(mysql, dashboard_id, session['user_id'], name=name, description=description)

        if success:
            return jsonify({'success': True, 'message': message}), 200
        status = 404 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_dashboards_bp.route('/reorder', methods=['POST'])
@api_login_required
def reorder_dashboards():
    """Sprint 19. Body: {order: [id1, id2, ...]} — the caller's full, new
    dashboard ordering. Every id is verified as owned by the session user
    before any write (Dashboard.reorder), so a payload naming someone
    else's dashboard is rejected in full, not partially applied."""
    try:
        data = request.get_json(silent=True) or {}
        order = data.get('order')
        if not isinstance(order, list) or not order:
            return jsonify({'success': False, 'message': 'order (non-empty list) is required'}), 400
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'order must be a list of dashboard ids'}), 400

        mysql = get_mysql()
        success, message = Dashboard.reorder(mysql, session['user_id'], order)
        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/delete', methods=['POST', 'DELETE'])
@api_login_required
def delete_dashboard(dashboard_id):
    mysql = get_mysql()
    success, message = Dashboard.delete(mysql, dashboard_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': message}), 200
    status = 404 if 'permission' in message else 400
    return jsonify({'success': False, 'message': message}), status


# ── Widgets ──────────────────────────────────────────────────────────────────

@api_dashboards_bp.route('/<int:dashboard_id>/widgets', methods=['GET'])
@api_login_required
def list_widgets(dashboard_id):
    mysql = get_mysql()
    widgets = DashboardWidget.get_by_dashboard(mysql, dashboard_id, session['user_id'])
    return jsonify({'success': True, 'widgets': [_widget_to_dict(w) for w in widgets]}), 200


@api_dashboards_bp.route('/<int:dashboard_id>/widgets/<int:widget_id>/update', methods=['POST', 'PUT'])
@api_login_required
def update_widget(dashboard_id, widget_id):
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = session['user_id']

        is_minimized = data.get('is_minimized')
        time_period = data.get('time_period')
        is_enabled = data.get('is_enabled')

        if is_minimized is not None and isinstance(is_minimized, str):
            is_minimized = is_minimized.lower() in ('true', '1')
        if is_enabled is not None and isinstance(is_enabled, str):
            is_enabled = is_enabled.lower() in ('true', '1')

        chart_type = data.get('chart_type', _UNSET)
        filter_config = data.get('filter_config', _UNSET)
        custom_title = data.get('custom_title', _UNSET)
        chart_colors = data.get('chart_colors', _UNSET)

        mysql = get_mysql()
        # Ownership verified inside update_state() via the JOIN to dashboards
        success = DashboardWidget.update_state(
            mysql, widget_id, user_id,
            is_minimized=is_minimized,
            time_period=time_period,
            is_enabled=is_enabled,
            chart_type=chart_type,
            filter_config=filter_config,
            custom_title=custom_title,
            chart_colors=chart_colors,
        )

        if success:
            return jsonify({'success': True, 'message': 'Widget updated'}), 200
        return jsonify({'success': False, 'message': 'Failed to update widget'}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/widgets/reorder', methods=['POST'])
@api_login_required
def reorder_widgets(dashboard_id):
    """Sprint 19. Body: {order: [widget_id1, widget_id2, ...]} — the new
    ordering for widgets within dashboard_id. DashboardWidget.reorder
    verifies dashboard_id belongs to the session user AND that every
    widget id in the payload belongs to dashboard_id, before any write."""
    try:
        data = request.get_json(silent=True) or {}
        order = data.get('order')
        if not isinstance(order, list) or not order:
            return jsonify({'success': False, 'message': 'order (non-empty list) is required'}), 400
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'order must be a list of widget ids'}), 400

        mysql = get_mysql()
        success, message = DashboardWidget.reorder(mysql, dashboard_id, session['user_id'], order)
        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/widgets/add', methods=['POST'])
@api_login_required
def add_widget(dashboard_id):
    try:
        data = request.get_json() if request.is_json else request.form
        widget_type = (data.get('widget_type') or '').strip()

        if not widget_type:
            return jsonify({'success': False, 'message': 'widget_type is required'}), 400

        mysql = get_mysql()
        user_id = session['user_id']
        widget_id = DashboardWidget.add_to_dashboard(mysql, dashboard_id, user_id, widget_type)

        if widget_id:
            widget = DashboardWidget.get_by_id(mysql, widget_id, user_id)
            return jsonify({'success': True, 'widget': _widget_to_dict(widget)}), 201
        return jsonify({'success': False, 'message': 'Invalid widget type, or dashboard not found'}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/widgets/<int:widget_id>/remove', methods=['POST', 'DELETE'])
@api_login_required
def remove_widget(dashboard_id, widget_id):
    mysql = get_mysql()
    success = DashboardWidget.remove(mysql, widget_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': 'Widget removed'}), 200
    return jsonify({'success': False, 'message': 'Widget not found or you don\'t have permission'}), 404


# ── Serialisers ──────────────────────────────────────────────────────────────

def _dashboard_to_dict(d):
    return {
        'id': d.id,
        'name': d.name,
        'description': d.description,
        'is_active': d.is_active,
        'sort_order': d.sort_order,
    }


def _widget_to_dict(w):
    return {
        'id': w.id,
        'dashboard_id': w.dashboard_id,
        'widget_type': w.widget_type,
        'title': w.title,
        'endpoint': w.endpoint,
        'is_enabled': w.is_enabled,
        'is_minimized': w.is_minimized,
        'time_period': w.time_period,
        'position': w.position,
        'chart_type': w.chart_type,
        'filter_config': w.filter_config,
        'custom_title': w.custom_title,
        'chart_colors': w.chart_colors,
    }
