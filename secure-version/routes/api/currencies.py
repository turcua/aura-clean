"""
Aura Financial Tracker - Secure Version
Currencies API Routes
Sprint 17 follow-up: dynamic currency list

Security properties: read/write require @api_login_required (currencies are
global/shared reference data, same trust model as exchange rates and
Release 3's shared default categories); currency_code and the starter rate
are both validated in Currency.create() before touching the DB.
"""

from flask import Blueprint, request, jsonify, current_app
from models.currency import Currency
from routes.main import api_login_required

api_currencies_bp = Blueprint('api_currencies', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_currencies_bp.route('/list', methods=['GET'])
@api_login_required
def list_currencies():
    mysql = get_mysql()
    currencies = Currency.get_all(mysql)
    return jsonify({'success': True, 'currencies': [_currency_to_dict(c) for c in currencies]}), 200


@api_currencies_bp.route('/create', methods=['POST'])
@api_login_required
def create_currency():
    data = request.get_json() if request.is_json else request.form
    code = data.get('code')
    initial_rate = data.get('initial_rate_to_base')

    mysql = get_mysql()
    success, message, created_code = Currency.create(mysql, code, initial_rate)
    if success:
        return jsonify({'success': True, 'message': message, 'code': created_code}), 201
    return jsonify({'success': False, 'message': message}), 400


def _currency_to_dict(c):
    return {
        'code': c.code,
        'is_base': c.is_base,
        'created_at': str(c.created_at) if c.created_at else None,
    }
