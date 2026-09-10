"""
Aura Financial Tracker - Vulnerable Version
AI Advisor API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 23: AI Advisor Foundation
"""

from flask import Blueprint, jsonify, request, session, current_app

from models.ai_conversation import AIConversation
from utils.groq_client import send_chat_completion
from utils.ai_context import build_system_prompt
from utils.ai_tools import TOOLS, execute_tool_call
from utils import flag_engine

api_ai_advisor_bp = Blueprint('api_ai_advisor', __name__)

MAX_HISTORY_MESSAGES = 20
DISPLAY_HISTORY_LIMIT = 100


def get_mysql():
    return current_app.extensions['mysql']


@api_ai_advisor_bp.route('/chat', methods=['POST'])
def chat():
    """
    VULNERABILITIES: No auth, IDOR — user_id from request body, SQL
    Injection (in the model), no rate limiting (unbounded real Groq API
    cost) — VULN-075.
    """
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = data.get('user_id')
        message = (data.get('message') or '').strip()
        if not user_id or not message:
            return jsonify({'success': False, 'message': 'user_id and message are required'}), 400

        mysql = get_mysql()
        AIConversation.add_message(mysql, user_id, 'user', message)

        system_prompt, ctf_secret = build_system_prompt(mysql, user_id)
        since = session.get('ai_chat_since')
        history = AIConversation.get_recent(mysql, user_id, limit=MAX_HISTORY_MESSAGES, since=since)

        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": m.role, "content": m.content} for m in history]

        api_key = current_app.config.get('GROQ_API_KEY')
        model = current_app.config.get('GROQ_MODEL')

        success, content, tool_calls = send_chat_completion(api_key, model, messages, tools=TOOLS)

        if not success:
            return jsonify({'success': False, 'message': content}), 502

        # VULNERABILITY (VULN-079): tool calls execute immediately, no
        # confirmation step, no re-validation beyond whatever Groq sent.
        if tool_calls:
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            for tc in tool_calls:
                result = execute_tool_call(mysql, user_id, tc)
                messages.append({"role": "tool", "tool_call_id": tc.get('id'), "content": result})

            success2, content2, _ = send_chat_completion(api_key, model, messages)
            if success2 and content2:
                content = content2

            # Sprint 44 (VULN-079 flag): a financial-write tool call
            # executing at all, with zero confirmation step, is the proof —
            # the vulnerability is that no gate exists, demonstrated by any
            # tool call actually running, injected or not.
            attacker_id = session.get('user_id')
            if attacker_id:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-079')

        AIConversation.add_message(mysql, user_id, 'assistant', content or '')

        # Sprint 43 (VULN-077 flag): Solis actually saying the "protected"
        # secret back is the proof the confidentiality instruction was
        # overridden — credited to whoever's really driving this session,
        # not the (possibly spoofed, per VULN-075) body-supplied user_id.
        if content and ctf_secret in content:
            attacker_id = session.get('user_id')
            if attacker_id:
                flag_engine.credit_exact_flag(mysql, attacker_id, 'VULN-077', ctf_secret)

        # Sprint 44 (VULN-075 flag): getting a real answer back for a
        # user_id that isn't the caller's own logged-in session is the
        # proof — same IDOR pattern already proven elsewhere, here reaching
        # Solis's chat endpoint specifically.
        attacker_id = session.get('user_id')
        if attacker_id and str(user_id) != str(attacker_id) and content:
            flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-075')

        return jsonify({'success': True, 'message': content}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_ai_advisor_bp.route('/history', methods=['GET'])
def history():
    """VULNERABILITY: No auth, IDOR — user_id from query string (VULN-075)"""
    try:
        user_id = request.args.get('user_id', '')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        since = session.get('ai_chat_since')
        messages = AIConversation.get_recent(mysql, user_id, limit=DISPLAY_HISTORY_LIMIT, since=since)
        return jsonify({
            'success': True,
            'messages': [_message_to_dict(m) for m in messages],
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_ai_advisor_bp.route('/clear', methods=['POST'])
def clear():
    """VULNERABILITY: No auth, IDOR — user_id from request body, can wipe
    another user's entire conversation history (VULN-075)"""
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        AIConversation.delete_all(mysql, user_id)
        return jsonify({'success': True, 'message': 'Conversation cleared'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _message_to_dict(m):
    return {
        'id': m.id,
        'user_id': m.user_id,  # VULN: Exposing user_id
        'role': m.role,
        'content': m.content,
        'created_at': str(m.created_at) if m.created_at else None,
    }
