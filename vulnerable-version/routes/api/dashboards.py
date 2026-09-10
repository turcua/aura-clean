"""
Aura Financial Tracker - Vulnerable Version
Dashboards API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 8: Flame Breathing - Eighth Form
"""

from flask import Blueprint, request, jsonify, session
from models.dashboard import Dashboard
from models.dashboard_widget import DashboardWidget, WIDGET_TITLES, WIDGET_ENDPOINTS, WIDGET_DEFAULT_PERIODS
from utils import flag_engine


def _dashboard_owner(mysql, dashboard_id):
    """Sprint 44 helper — safe, parameterized. Dashboard has no get_by_id()
    of its own (only get_all_by_user), so this fills that gap purely for
    flag-credit ownership checks, never for the app's own vulnerable logic."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT user_id FROM dashboards WHERE id = %s", (dashboard_id,))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None
    except Exception:
        return None


def _widget_dashboard_owner(mysql, widget_id):
    """Sprint 44 helper — safe, parameterized. Resolves the real owner of
    the dashboard a widget belongs to, for flag-credit ownership checks."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT d.user_id FROM dashboard_widgets w "
            "JOIN dashboards d ON w.dashboard_id = d.id WHERE w.id = %s",
            (widget_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None
    except Exception:
        return None

api_dashboards_bp = Blueprint('api_dashboards', __name__)


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


# ── Dashboards ───────────────────────────────────────────────────────────────

@api_dashboards_bp.route('/list', methods=['GET'])
def list_dashboards():
    """
    Returns all dashboards for the user.
    Auto-seeds 4 default dashboards if the user has none.
    VULNERABILITIES: No auth check, IDOR via user_id, SQL Injection
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        dashboards = Dashboard.get_all_by_user(mysql, user_id)

        if not dashboards:
            # VULN: Auto-seed triggered by unauthenticated user_id
            Dashboard.create_defaults_for_user(mysql, user_id)
            dashboards = Dashboard.get_all_by_user(mysql, user_id)

        # Sprint 44 (VULN-058 flag): listing someone else's dashboards via
        # the user_id param is the proof.
        attacker_id = session.get('user_id')
        if attacker_id and str(user_id) != str(attacker_id):
            flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-058')

        return jsonify({
            'success': True,
            'dashboards': [_dashboard_to_dict(d) for d in dashboards]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/activate', methods=['POST'])
def activate_dashboard(dashboard_id):
    """
    Sets the given dashboard as active for the user.
    VULNERABILITIES: No auth, IDOR — any user_id + dashboard_id pair accepted
    """
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        # VULN: No ownership verification
        success = Dashboard.set_active(mysql, user_id, dashboard_id)

        if success:
            # Sprint 44 (VULN-061 flag): activating a dashboard under a
            # user_id that isn't the caller's own logged-in session is the
            # proof.
            attacker_id = session.get('user_id')
            if attacker_id and str(user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-061')
            return jsonify({'success': True, 'message': 'Dashboard activated'}), 200
        return jsonify({'success': False, 'message': 'Failed to activate dashboard'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/reorder', methods=['POST'])
def reorder_dashboards():
    """
    Sprint 19. Body: {order: [id1, id2, ...], user_id}.
    VULNERABILITY (VULN-070): No auth, no CSRF, no ownership check — the
    order list is applied to whatever dashboard ids are given, regardless
    of who owns them. user_id is accepted but never actually checked
    against the dashboards being reordered.
    """
    try:
        data = request.get_json() if request.is_json else request.form
        order = data.get('order')
        if not order:
            return jsonify({'success': False, 'message': 'order is required'}), 400

        mysql = get_mysql()
        # VULN: No ownership check on any id in order
        success = Dashboard.reorder(mysql, order)

        if success:
            # Sprint 44 (VULN-070 flag): reordering a dashboard id that
            # isn't among the caller's own is the proof.
            attacker_id = session.get('user_id')
            if attacker_id:
                own_ids = {d.id for d in Dashboard.get_all_by_user(mysql, attacker_id)}
                if any(str(oid) not in {str(i) for i in own_ids} for oid in order):
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-070')
            return jsonify({'success': True, 'message': 'Dashboard order updated'}), 200
        return jsonify({'success': False, 'message': 'Failed to reorder dashboards'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── Widgets ──────────────────────────────────────────────────────────────────

@api_dashboards_bp.route('/<int:dashboard_id>/widgets', methods=['GET'])
def list_widgets(dashboard_id):
    """
    Returns all widgets for a dashboard.
    VULNERABILITIES: No auth, IDOR — dashboard_id not validated against session user
    """
    try:
        mysql = get_mysql()
        widgets = DashboardWidget.get_by_dashboard(mysql, dashboard_id)

        # Sprint 44 (VULN-059 + VULN-063 flags): reading a dashboard's
        # widgets that isn't the caller's own is the proof for both —
        # VULN-059 (the IDOR itself, no ownership check on dashboard_id)
        # and VULN-063 (this endpoint requires zero authentication at all,
        # not even a user_id param) are both demonstrated by the same
        # single request.
        attacker_id = session.get('user_id')
        if attacker_id:
            real_owner = _dashboard_owner(mysql, dashboard_id)
            if real_owner is not None and str(real_owner) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-059')
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-063')

        return jsonify({
            'success': True,
            'widgets': [_widget_to_dict(w) for w in widgets]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/widgets/<int:widget_id>/update', methods=['POST', 'PUT'])
def update_widget(dashboard_id, widget_id):
    """
    Updates widget state: is_minimized, time_period, is_enabled, chart_type, filter_config, custom_title.
    VULNERABILITIES: No auth, IDOR on widget_id, SQL Injection via time_period, chart_type, custom_title
    VULNERABILITY: dashboard_id is accepted but not used — any widget_id can be modified
    VULNERABILITY: custom_title rendered via innerHTML → Stored XSS
    """
    try:
        data = request.get_json() if request.is_json else request.form

        is_minimized = data.get('is_minimized')
        time_period  = data.get('time_period')
        is_enabled   = data.get('is_enabled')

        # Convert string booleans from form data
        if is_minimized is not None and isinstance(is_minimized, str):
            is_minimized = is_minimized.lower() in ('true', '1')
        if is_enabled is not None and isinstance(is_enabled, str):
            is_enabled = is_enabled.lower() in ('true', '1')

        # Sprint 9b fields — use sentinel to distinguish "not in request" from explicit null
        _UNSET       = '__unset__'
        chart_type    = data.get('chart_type',    _UNSET)
        filter_config = data.get('filter_config', _UNSET)
        custom_title  = data.get('custom_title',  _UNSET)
        chart_colors  = data.get('chart_colors',  _UNSET)

        mysql = get_mysql()
        # VULN: No ownership check — widget_id accepted directly
        success = DashboardWidget.update_state(
            mysql, widget_id,
            is_minimized=is_minimized,
            time_period=time_period,
            is_enabled=is_enabled,
            chart_type=None   if chart_type    == _UNSET else chart_type,
            filter_config=None if filter_config == _UNSET else filter_config,
            custom_title=None  if custom_title  == _UNSET else custom_title,
            chart_colors=None  if chart_colors  == _UNSET else chart_colors,
            _chart_type_set=chart_type    != _UNSET,
            _filter_config_set=filter_config != _UNSET,
            _custom_title_set=custom_title  != _UNSET,
            _chart_colors_set=chart_colors  != _UNSET,
        )

        if success:
            attacker_id = session.get('user_id')
            if attacker_id:
                # Sprint 44 (VULN-062 flag): updating a widget that isn't
                # on one of the caller's own dashboards is the proof.
                real_owner = _widget_dashboard_owner(mysql, widget_id)
                if real_owner is not None and str(real_owner) != str(attacker_id):
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-062')

                # Sprint 44 (VULN-057 flag): a literal quote in custom_title
                # that the update still accepted is real injected SQL
                # syntax — a legitimate title essentially never contains one.
                if custom_title not in (None, _UNSET) and "'" in str(custom_title):
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-057')

            return jsonify({'success': True, 'message': 'Widget updated'}), 200
        return jsonify({'success': False, 'message': 'Failed to update widget'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/widgets/reorder', methods=['POST'])
def reorder_widgets(dashboard_id):
    """
    Sprint 19. Body: {order: [widget_id1, widget_id2, ...], user_id}.
    VULNERABILITY (VULN-070/071): No auth, no CSRF. dashboard_id is taken
    from the URL but never checked against the caller's ownership, and
    none of the widget ids in order are verified as actually belonging to
    dashboard_id — a widget id from a different dashboard is accepted and
    silently repositioned anyway.
    """
    try:
        data = request.get_json() if request.is_json else request.form
        order = data.get('order')
        if not order:
            return jsonify({'success': False, 'message': 'order is required'}), 400

        mysql = get_mysql()
        # VULN: dashboard_id unused for validation, no ownership/membership check on order
        success = DashboardWidget.reorder(mysql, dashboard_id, order)

        if success:
            # Sprint 44 (VULN-071 flag): a widget id in `order` that doesn't
            # actually belong to dashboard_id is the proof — dashboard_id
            # is taken from the URL but never used to validate membership.
            attacker_id = session.get('user_id')
            if attacker_id:
                own_widget_ids = {w.id for w in DashboardWidget.get_by_dashboard(mysql, dashboard_id)}
                if any(str(wid) not in {str(i) for i in own_widget_ids} for wid in order):
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-071')
            return jsonify({'success': True, 'message': 'Widget order updated'}), 200
        return jsonify({'success': False, 'message': 'Failed to reorder widgets'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/create', methods=['POST'])
def create_dashboard():
    """
    Creates a new named dashboard for the user.
    VULNERABILITIES: No auth check, no CSRF token, SQL Injection via name,
                     Mass assignment — user_id taken from request body not session
    """
    try:
        data        = request.get_json() if request.is_json else request.form
        # VULN: user_id from request body — mass assignment
        user_id     = data.get('user_id')
        name        = (data.get('name') or '').strip()
        description = (data.get('description') or '').strip()

        if not user_id or not name:
            return jsonify({'success': False, 'message': 'user_id and name are required'}), 400

        mysql        = get_mysql()
        dashboard_id = Dashboard.create(mysql, user_id, name, description)

        if dashboard_id:
            # Sprint 44 (VULN-052 flag): the write succeeding under a
            # user_id that isn't the caller's own logged-in session is the
            # proof — same pattern already proven on VULN-022.
            attacker_id = session.get('user_id')
            if attacker_id and str(user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-052')

            # Sprint 44 (VULN-053 flag): same Origin/Referer-mismatch
            # signature already proven on VULN-024/010 — a genuine
            # cross-site request succeeding is the proof there's no CSRF
            # token on this dashboard/widget CRUD endpoint.
            origin = request.headers.get('Origin') or request.headers.get('Referer') or ''
            if not request.is_json and origin and request.host not in origin and attacker_id:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-053')

            dashboards   = Dashboard.get_all_by_user(mysql, user_id)
            new_dash     = next((d for d in dashboards if d.id == dashboard_id), None)
            return jsonify({
                'success':   True,
                'dashboard': _dashboard_to_dict(new_dash) if new_dash else {'id': dashboard_id}
            }), 201
        return jsonify({'success': False, 'message': 'Failed to create dashboard'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/update', methods=['POST', 'PUT'])
def update_dashboard(dashboard_id):
    """
    Renames a dashboard or updates its description.
    VULNERABILITIES: No auth, no CSRF, IDOR — any dashboard_id accepted,
                     SQL Injection via name and description
    """
    try:
        data        = request.get_json() if request.is_json else request.form
        name        = data.get('name')
        if name is not None:
            name = name.strip() or None
        description = data.get('description')
        if description is not None:
            description = description.strip()

        mysql   = get_mysql()
        # VULN: No ownership check
        real_owner = _dashboard_owner(mysql, dashboard_id)
        success = Dashboard.update(mysql, dashboard_id, name=name, description=description)

        if success:
            attacker_id = session.get('user_id')
            if attacker_id:
                # Sprint 44 (VULN-048 flag): updating a dashboard that
                # isn't the caller's own is the proof.
                if real_owner is not None and str(real_owner) != str(attacker_id):
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-048')

                # Sprint 44 (VULN-046 flag): a literal quote in the name
                # that the update still accepted is real injected SQL
                # syntax — a legitimate name essentially never contains one.
                if name and "'" in str(name):
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-046')

            return jsonify({'success': True, 'message': 'Dashboard updated'}), 200
        return jsonify({'success': False, 'message': 'Failed to update dashboard'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/delete', methods=['POST', 'DELETE'])
def delete_dashboard(dashboard_id):
    """
    Deletes a dashboard and all its widgets (CASCADE).
    VULNERABILITIES: No auth, no CSRF, IDOR — any dashboard_id accepted
    """
    try:
        mysql   = get_mysql()
        real_owner = _dashboard_owner(mysql, dashboard_id)
        # VULN: No ownership check
        success = Dashboard.delete(mysql, dashboard_id)

        if success:
            # Sprint 44 (VULN-049 flag): deleting a dashboard that isn't
            # the caller's own is the proof.
            attacker_id = session.get('user_id')
            if attacker_id and real_owner is not None and str(real_owner) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-049')
            return jsonify({'success': True, 'message': 'Dashboard deleted'}), 200
        return jsonify({'success': False, 'message': 'Failed to delete dashboard'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/widgets/add', methods=['POST'])
def add_widget(dashboard_id):
    """
    Adds a widget of the given type to the dashboard.
    VULNERABILITIES: No auth, no CSRF, IDOR on dashboard_id,
                     SQL Injection via widget_type
    """
    try:
        data        = request.get_json() if request.is_json else request.form
        widget_type = (data.get('widget_type') or '').strip()

        if not widget_type:
            return jsonify({'success': False, 'message': 'widget_type is required'}), 400

        mysql     = get_mysql()
        # VULN: No ownership check, SQL Injection via widget_type passed directly
        widget_id = DashboardWidget.add_to_dashboard(mysql, dashboard_id, widget_type)

        if widget_id:
            # Sprint 44 (VULN-050 flag): adding a widget to a dashboard
            # that isn't the caller's own is the proof.
            attacker_id = session.get('user_id')
            if attacker_id:
                real_owner = _dashboard_owner(mysql, dashboard_id)
                if real_owner is not None and str(real_owner) != str(attacker_id):
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-050')

            widgets  = DashboardWidget.get_by_dashboard(mysql, dashboard_id)
            new_w    = next((w for w in widgets if w.id == widget_id), None)
            return jsonify({
                'success': True,
                'widget':  _widget_to_dict(new_w) if new_w else {'id': widget_id}
            }), 201
        return jsonify({'success': False, 'message': 'Failed to add widget'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_dashboards_bp.route('/<int:dashboard_id>/widgets/<int:widget_id>/remove', methods=['POST', 'DELETE'])
def remove_widget(dashboard_id, widget_id):
    """
    Permanently removes a widget from the dashboard.
    VULNERABILITIES: No auth, no CSRF, IDOR on widget_id
    VULNERABILITY: dashboard_id is not used — any widget_id can be removed
    """
    try:
        mysql   = get_mysql()
        real_owner = _widget_dashboard_owner(mysql, widget_id)
        # VULN: No ownership check — widget_id accepted without verification
        success = DashboardWidget.remove(mysql, widget_id)

        if success:
            # Sprint 44 (VULN-051 flag): removing a widget that isn't on
            # one of the caller's own dashboards is the proof.
            attacker_id = session.get('user_id')
            if attacker_id and real_owner is not None and str(real_owner) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-051')
            return jsonify({'success': True, 'message': 'Widget removed'}), 200
        return jsonify({'success': False, 'message': 'Failed to remove widget'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── Serialisers ──────────────────────────────────────────────────────────────

def _dashboard_to_dict(d):
    return {
        'id':          d.id,
        'user_id':     d.user_id,   # VULN: Exposed in response
        'name':        d.name,
        'description': d.description,
        'is_active':   d.is_active,
        'sort_order':  d.sort_order,
    }


def _widget_to_dict(w):
    return {
        'id':            w.id,
        'dashboard_id':  w.dashboard_id,
        'widget_type':   w.widget_type,
        'title':         w.title,
        'endpoint':      w.endpoint,
        'is_enabled':    w.is_enabled,
        'is_minimized':  w.is_minimized,
        'time_period':   w.time_period,
        'position':      w.position,
        'chart_type':    w.chart_type,    # Sprint 9b
        'filter_config': w.filter_config, # Sprint 9b — dict or None
        'custom_title':  w.custom_title,  # Sprint 9b
        'chart_colors':  w.chart_colors,  # Sprint 20 — dict or None
    }
