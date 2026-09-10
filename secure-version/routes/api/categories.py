"""
Aura Financial Tracker - Secure Version
Category API Routes
Sprint 11: Core Financial Tracking

Security properties (contrast with vulnerable-version/routes/api/categories.py):
- Every route requires @api_login_required
- user_id always comes from session, never from the request body/params
- Ownership enforced at the model layer (id = %s AND user_id = %s)
"""

import re
from flask import Blueprint, request, jsonify, session, current_app
from models.category import Category
from routes.main import api_login_required

api_categories_bp = Blueprint('api_categories', __name__)

HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')


def get_mysql():
    return current_app.extensions['mysql']


def _validate_color(color):
    """
    Only a strict 6-digit hex code is accepted. Category colour is rendered
    into a `style="background:${color}"` attribute client-side — an unvalidated
    value (e.g. containing a quote and a tag) would be a stored-XSS vector there,
    so this is the boundary that stops it.
    """
    if not color:
        return '#6c757d'
    return color if HEX_COLOR_RE.match(color) else None


@api_categories_bp.route('/create', methods=['POST'])
@api_login_required
def create_category():
    """Create a category owned by the session user."""
    try:
        data = request.get_json() if request.is_json else request.form
        name = (data.get('name') or '').strip()
        type = data.get('type')
        color = _validate_color(data.get('color', '#6c757d'))

        if not name or type not in ('income', 'expense'):
            return jsonify({'success': False, 'message': 'name and a valid type are required'}), 400
        if len(name) > 100:
            return jsonify({'success': False, 'message': 'name is too long (max 100 characters)'}), 400
        if color is None:
            return jsonify({'success': False, 'message': 'color must be a 6-digit hex code, e.g. #3d7bff'}), 400

        mysql = get_mysql()
        success, message, category_id = Category.create(mysql, session['user_id'], name, type, color)

        if success:
            return jsonify({'success': True, 'message': message, 'category_id': category_id}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_categories_bp.route('/<int:category_id>', methods=['GET'])
@api_login_required
def get_category(category_id):
    """Get a single category — visible only if owned by the session user or a default."""
    try:
        mysql = get_mysql()
        category = Category.get_by_id(mysql, category_id, session['user_id'])
        if category:
            return jsonify({'success': True, 'category': _category_to_dict(category)}), 200
        return jsonify({'success': False, 'message': 'Category not found'}), 404
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_categories_bp.route('/<int:category_id>/update', methods=['PUT', 'POST'])
@api_login_required
def update_category(category_id):
    """Update a category — model layer enforces id = %s AND user_id = %s ownership."""
    try:
        data = request.get_json() if request.is_json else request.form
        name = (data.get('name') or '').strip()
        type = data.get('type')
        color = _validate_color(data.get('color'))

        if not name or type not in ('income', 'expense'):
            return jsonify({'success': False, 'message': 'name and a valid type are required'}), 400
        if color is None:
            return jsonify({'success': False, 'message': 'color must be a 6-digit hex code, e.g. #3d7bff'}), 400

        mysql = get_mysql()
        success, message = Category.update(mysql, category_id, session['user_id'], name, type, color)

        if success:
            return jsonify({'success': True, 'message': message}), 200
        status = 403 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_categories_bp.route('/<int:category_id>/delete', methods=['DELETE', 'POST'])
@api_login_required
def delete_category(category_id):
    """Delete a category — model layer enforces id = %s AND user_id = %s ownership."""
    try:
        mysql = get_mysql()
        success, message = Category.delete(mysql, category_id, session['user_id'])

        if success:
            return jsonify({'success': True, 'message': message}), 200
        status = 403 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_categories_bp.route('/list', methods=['GET'])
@api_login_required
def list_categories():
    """List categories visible to the session user (their own + system defaults)."""
    try:
        type = request.args.get('type')
        mysql = get_mysql()
        categories = Category.get_all_by_user(mysql, session['user_id'], type)

        return jsonify({
            'success': True,
            'count': len(categories),
            'categories': [_category_to_dict(c) for c in categories],
        }), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


def _category_to_dict(c):
    return {
        'id': c.id,
        'name': c.name,
        'type': c.type,
        'color': c.color,
        'is_default': c.is_default,
    }
