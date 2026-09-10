"""
Aura Financial Tracker - Secure Version
Exchange Rates API Routes
Sprint 17: Multi-Currency (static rates)

Security properties: read/write require @api_login_required (rates are
global/shared reference data, editable by any authenticated user — same
trust model as Release 3's shared default categories); currency_code and
rate_to_base are both validated in the model before touching the DB.
"""

from flask import Blueprint, request, jsonify, current_app
from models.exchange_rate import ExchangeRate
from models.currency import Currency
from routes.main import api_login_required
from utils.currency import get_rate_map, convert

api_exchange_rates_bp = Blueprint('api_exchange_rates', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_exchange_rates_bp.route('/list', methods=['GET'])
@api_login_required
def list_rates():
    mysql = get_mysql()
    rates = ExchangeRate.get_all(mysql)
    result = [{'currency_code': 'RON', 'rate_to_base': 1.0, 'updated_at': None, 'is_base': True}]
    result += [_rate_to_dict(r) for r in rates]
    return jsonify({'success': True, 'rates': result}), 200


@api_exchange_rates_bp.route('/<string:currency_code>/update', methods=['POST'])
@api_login_required
def update_rate(currency_code):
    data = request.get_json() if request.is_json else request.form
    rate_to_base = data.get('rate_to_base')

    mysql = get_mysql()
    success, message = ExchangeRate.update_rate(mysql, currency_code.upper(), rate_to_base)
    if success:
        return jsonify({'success': True, 'message': message}), 200
    return jsonify({'success': False, 'message': message}), 400


@api_exchange_rates_bp.route('/<string:currency_code>/delete', methods=['POST', 'DELETE'])
@api_login_required
def delete_rate(currency_code):
    mysql = get_mysql()
    success, message = ExchangeRate.delete(mysql, currency_code.upper())
    if success:
        return jsonify({'success': True, 'message': message}), 200
    return jsonify({'success': False, 'message': message}), 400


@api_exchange_rates_bp.route('/convert', methods=['GET'])
@api_login_required
def convert_amount():
    raw_amount = request.args.get('amount')
    from_currency = (request.args.get('from') or '').upper()
    to_currency = (request.args.get('to') or '').upper()

    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'amount must be a number'}), 400

    mysql = get_mysql()
    all_currencies = {c.code for c in Currency.get_all(mysql)}
    if from_currency not in all_currencies or to_currency not in all_currencies:
        return jsonify({'success': False, 'message': 'Unsupported currency'}), 400

    rate_map = get_rate_map(mysql)
    result = convert(amount, from_currency, to_currency, rate_map)
    if result is None:
        return jsonify({'success': False, 'message': 'No rate available for that currency'}), 400
    return jsonify({'success': True, 'result': round(result, 6)}), 200


def _rate_to_dict(r):
    return {
        'currency_code': r.currency_code,
        'rate_to_base': r.rate_to_base,
        'updated_at': str(r.updated_at) if r.updated_at else None,
        'is_base': False,
    }
