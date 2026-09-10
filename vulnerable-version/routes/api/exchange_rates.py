"""
Aura Financial Tracker - Vulnerable Version
Exchange Rates API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 17: Multi-Currency (static rates)
"""

from flask import Blueprint, request, jsonify, current_app, session
from models.exchange_rate import ExchangeRate
from utils.currency import get_rate_map, convert
from utils import flag_engine

api_exchange_rates_bp = Blueprint('api_exchange_rates', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_exchange_rates_bp.route('/list', methods=['GET'])
def list_rates():
    """VULNERABILITY: No auth required"""
    mysql = get_mysql()
    rates = ExchangeRate.get_all(mysql)
    result = [{'currency_code': 'RON', 'rate_to_base': 1.0, 'updated_at': None, 'is_base': True}]
    result += [_rate_to_dict(r) for r in rates]
    return jsonify({'success': True, 'rates': result}), 200


@api_exchange_rates_bp.route('/<string:currency_code>/update', methods=['POST'])
def update_rate(currency_code):
    """
    VULNERABILITIES: No auth, No CSRF, VULN-064 (no rate bounds check),
    VULN-065 (SQL injection in the model), VULN-066 (currency_code taken
    straight from the URL, not restricted to EUR/USD/IDR — arbitrary text,
    including HTML/JS, is stored and later rendered client-side)
    """
    try:
        data = request.get_json() if request.is_json else request.form
        rate_to_base = data.get('rate_to_base', 0)

        mysql = get_mysql()
        success, message = ExchangeRate.update_rate(mysql, currency_code, rate_to_base)
        if success:
            # Sprint 44 (VULN-064 flag, weak fit like VULN-034/035/045 —
            # business-logic bugs don't leak data): credited when a
            # genuinely unrealistic rate (negative, zero, or absurdly
            # large) is accepted with no bounds check — the exact scenario
            # the bug describes.
            try:
                rate_val = float(rate_to_base)
                if rate_val <= 0 or rate_val > 1000:
                    attacker_id = session.get('user_id')
                    if attacker_id:
                        flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-064')
            except (TypeError, ValueError):
                pass
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_exchange_rates_bp.route('/<int:rate_id>/delete', methods=['POST', 'DELETE'])
def delete_rate(rate_id):
    """VULNERABILITIES: No auth, No CSRF, IDOR (no ownership concept at all for this global data)"""
    mysql = get_mysql()
    success, message = ExchangeRate.delete(mysql, rate_id)
    if success:
        return jsonify({'success': True, 'message': message}), 200
    return jsonify({'success': False, 'message': message}), 400


@api_exchange_rates_bp.route('/convert', methods=['GET'])
def convert_amount():
    """VULNERABILITY: No auth. No validation on currency codes — anything
    not in the rate map is silently treated as a 1:1 rate (see utils.currency.convert)."""
    try:
        amount = float(request.args.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'amount must be a number'}), 400
    from_currency = request.args.get('from', 'RON')
    to_currency = request.args.get('to', 'RON')

    mysql = get_mysql()
    rate_map = get_rate_map(mysql)
    try:
        result = convert(amount, from_currency, to_currency, rate_map)
        return jsonify({'success': True, 'result': result}), 200
    except ZeroDivisionError:
        return jsonify({'success': False, 'message': 'Division by zero — target currency has a rate of 0'}), 500


def _rate_to_dict(r):
    return {
        'id': r.id,
        'currency_code': r.currency_code,
        'rate_to_base': r.rate_to_base,
        'updated_at': str(r.updated_at) if r.updated_at else None,
        'is_base': False,
    }
