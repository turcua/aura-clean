"""
Aura Financial Tracker - Vulnerable Version
Groq API Client Wrapper
Sprint 23: AI Advisor Foundation

The client itself isn't where this version's vulnerabilities live (those
are in the route/model layer — IDOR, SQL injection, insecure key storage).
This wrapper is intentionally close to identical to secure-version's,
except errors are passed through raw rather than generalized, matching
this version's established pattern of leaking exception detail to the
client (see routes/api/notifications.py's `f'Server error: {str(e)}'`).
"""

import logging

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)

# Sprint 32 follow-up: once a tool_use_failed retry drops `tools` entirely,
# a model that still "needs" to perform a write sometimes improvises rather
# than giving a plain answer — either faking tool-call syntax as text, or
# flatly denying it has any write capability at all. Neither reflects this
# app's real capability, so a retried response containing any of these is
# replaced with an honest failure message instead of being forwarded as-is.
_CONFUSED_RETRY_MARKERS = (
    '<function',
    "don't have the ability",
    "do not have the ability",
    "not capable of",
    "large language model",
    "as an ai",
    "consult with a financial advisor",
)


def _looks_like_confused_retry(content):
    if not content:
        return False
    lowered = content.lower()
    return any(marker in lowered for marker in _CONFUSED_RETRY_MARKERS)


def send_chat_completion(api_key, model, messages, tools=None):
    """
    messages: list of {"role": "system"|"user"|"assistant"|"tool", "content": str, ...}
    tools (Sprint 26, optional): Groq/OpenAI-compatible tool schemas — see utils/ai_tools.py
    Returns (success: bool, content: str|None, tool_calls: list).
    """
    if not api_key:
        return False, "AI advisor is not configured (missing API key)", []

    payload = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        return True, message.get("content"), message.get("tool_calls") or []
    except requests.exceptions.HTTPError as e:
        # VULNERABILITY: raw exception text AND the upstream response body
        # returned to the caller (info disclosure) — raise_for_status()'s own
        # message only has the status code and URL, not Groq's actual stated
        # reason for a 4xx, so this is the only way to see it (Sprint 32).
        body = e.response.text if e.response is not None else ''
        # A model can spontaneously (and malformedly) attempt a tool call
        # even for a question that doesn't need one — Groq reports this as
        # a 400 "tool_use_failed". Retried once without tools so the user
        # still gets a real answer, instead of the whole turn failing over
        # a tool call nobody asked for (a small, undocumented taste of the
        # same excessive-agency territory VULN-079 covers more seriously
        # for tool calls that actually succeed).
        if tools and 'tool_use_failed' in body:
            logger.warning("Groq tool_use_failed, retrying without tools: %s", body)
            retry_success, retry_content, retry_tool_calls = send_chat_completion(api_key, model, messages, tools=None)
            if retry_success and _looks_like_confused_retry(retry_content):
                return True, "I wasn't able to complete that action due to a formatting issue — please try rephrasing your request.", []
            return retry_success, retry_content, retry_tool_calls
        return False, f"AI advisor error: {str(e)} — {body}", []
    except Exception as e:
        # VULNERABILITY: raw exception text returned to the caller (info
        # disclosure), matching the pattern already established for every
        # other endpoint in this version (e.g. VULN-072's verbose errors).
        return False, f"AI advisor error: {str(e)}", []
