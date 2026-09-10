"""
Aura Financial Tracker - Vulnerable Version
Category API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 2: Thunder Breathing - Second Form

API Endpoints for AJAX operations - Returns JSON responses
"""

from flask import Blueprint, request, jsonify, session
from models.category import Category
from utils import flag_engine

# Create API blueprint
api_categories_bp = Blueprint('api_categories', __name__)

def get_mysql():
    """Get MySQL instance from current app"""
    from flask import current_app
    return current_app.extensions['mysql']

# ============================================================================
# CREATE CATEGORY
# ============================================================================
@api_categories_bp.route('/create', methods=['POST'])
def create_category():
    """
    Create a new category
    
    VULNERABILITIES:
    - No authentication check
    - SQL Injection in all fields
    - XSS in name and icon fields
    - Mass assignment (user_id can be manipulated)
    - No CSRF protection
    - No input validation
    """
    try:
        # VULN: No authentication check
        # VULN: No CSRF token validation
        
        # Get data from request
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        user_id = data.get('user_id')
        name = data.get('name')
        type = data.get('type')
        color = data.get('color', '#6c757d')

        # VULN: No input validation
        # VULN: XSS in name field

        if not all([user_id, name, type]):
            return jsonify({
                'success': False,
                'message': 'user_id, name, and type are required'
            }), 400

        mysql = get_mysql()
        success, message, category_id = Category.create(
            mysql, user_id, name, type, color
        )

        if success:
            # Sprint 44 (VULN-016 flag): a literal quote in the name field
            # that the insert still accepted is real injected SQL syntax —
            # a legitimate category name essentially never contains one.
            if name and "'" in str(name):
                sqli_attacker_id = session.get('user_id')
                if sqli_attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, sqli_attacker_id, 'VULN-016')

            # Sprint 44 (VULN-010 flag): same Origin/Referer-mismatch
            # signature already proven on VULN-024 — a genuine cross-site
            # request succeeding is the proof there's no CSRF token here.
            origin = request.headers.get('Origin') or request.headers.get('Referer') or ''
            if not request.is_json and origin and request.host not in origin:
                csrf_victim_id = session.get('user_id')
                if csrf_victim_id:
                    flag_engine.mark_solved_with_flag(mysql, csrf_victim_id, 'VULN-010')

            return jsonify({
                'success': True,
                'message': message,
                'category_id': category_id
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# GET SINGLE CATEGORY
# ============================================================================
@api_categories_bp.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """
    Get a single category by ID
    
    VULNERABILITIES:
    - No authentication check
    - IDOR - Can access any category
    - SQL Injection in category_id
    """
    try:
        # VULN: No authentication check
        # VULN: No ownership verification
        
        mysql = get_mysql()
        category = Category.get_by_id(mysql, category_id)

        if category:
            # Sprint 44 (VULN-019 flag): genuinely reading someone else's
            # category via the IDOR is the proof.
            attacker_id = session.get('user_id')
            if attacker_id and str(category.user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-019')

            return jsonify({
                'success': True,
                'category': {
                    'id': category.id,
                    'user_id': category.user_id,  # VULN: Exposing user_id
                    'name': category.name,
                    'type': category.type,
                    'color': category.color,
                    'is_default': category.is_default
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Category not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# UPDATE CATEGORY
# ============================================================================
@api_categories_bp.route('/<int:category_id>/update', methods=['PUT', 'POST'])
def update_category(category_id):
    """
    Update a category
    
    VULNERABILITIES:
    - No authentication check
    - IDOR - Can update any category
    - SQL Injection in all fields
    - XSS in name and icon
    - Mass assignment
    """
    try:
        # VULN: No authentication check
        # VULN: No ownership verification
        
        # Get data from request
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        user_id = data.get('user_id')
        name = data.get('name')
        type = data.get('type')
        color = data.get('color')

        # VULN: No input validation
        # VULN: Can change user_id (mass assignment)

        mysql = get_mysql()
        success, message = Category.update(
            mysql, category_id, user_id, name, type, color
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# DELETE CATEGORY
# ============================================================================
@api_categories_bp.route('/<int:category_id>/delete', methods=['DELETE', 'POST'])
def delete_category(category_id):
    """
    Delete a category
    
    VULNERABILITIES:
    - No authentication check
    - IDOR - Can delete any category
    - SQL Injection
    - No cascade handling (orphaned transactions)
    """
    try:
        # VULN: No authentication check
        # VULN: No ownership verification
        # VULN: No check for transactions using this category
        
        mysql = get_mysql()
        success, message = Category.delete(mysql, category_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# LIST CATEGORIES
# ============================================================================
@api_categories_bp.route('/list', methods=['GET'])
def list_categories():
    """
    List categories for a user, optionally filtered by type
    
    VULNERABILITIES:
    - SQL Injection in parameters
    - IDOR - Can list any user's categories
    - XSS in category names (reflected in response)
    """
    try:
        user_id = request.args.get('user_id')
        type = request.args.get('type')  # 'income', 'expense', or None for all
        
        # VULN: No authentication check
        # VULN: No ownership verification
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'user_id is required'
            }), 400
        
        mysql = get_mysql()
        categories = Category.get_all_by_user(mysql, user_id, type)
        
        # Format response
        category_list = []
        for c in categories:
            category_list.append({
                'id': c.id,
                'user_id': c.user_id,  # VULN: Exposing user_id
                'name': c.name,        # VULN: XSS if not escaped
                'type': c.type,
                'color': c.color,
                'is_default': c.is_default
            })
        
        return jsonify({
            'success': True,
            'count': len(category_list),
            'categories': category_list
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500
