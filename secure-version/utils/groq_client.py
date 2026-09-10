"""
Aura Financial Tracker - Secure Version
Groq API Client Wrapper
Sprint 23: AI Advisor Foundation

Thin wrapper around Groq's OpenAI-compatible Chat Completions endpoint.
Takes api_key/model as explicit arguments (rather than reading Flask config
itself) so it stays a plain, testable function — the route layer is
responsible for pulling GROQ_API_KEY/GROQ_MODEL out of current_app.config.
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
    On failure, content carries the error message and tool_calls is [].
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
        # Sprint 32: a model can spontaneously (and malformedly) attempt a
        # tool call even for a question that doesn't need one at all — Groq
        # reports this as a 400 "tool_use_failed". Retried once without
        # tools so the user still gets a real answer, rather than the whole
        # turn failing over a tool call nobody asked for.
        body = e.response.text if e.response is not None else ''
        if tools and 'tool_use_failed' in body:
            # Logged (not just checked) so the exact rejection reason — often
            # including Groq's own `failed_generation` field showing what the
            # model actually tried to call — is visible for root-causing the
            # next occurrence, instead of being usable only for this substring
            # check and then discarded.
            logger.warning("Groq tool_use_failed, retrying without tools: %s", body)
            retry_success, retry_content, retry_tool_calls = send_chat_completion(api_key, model, messages, tools=None)
            if retry_success and _looks_like_confused_retry(retry_content):
                return True, "I wasn't able to complete that action due to a formatting issue — please try rephrasing your request.", []
            return retry_success, retry_content, retry_tool_calls
        return False, "The AI advisor is temporarily unavailable. Please try again shortly.", []
    except requests.exceptions.RequestException:
        # Generic message only — never surface raw exception text (which
        # could include request details) back to the caller.
        return False, "The AI advisor is temporarily unavailable. Please try again shortly.", []
    except (KeyError, IndexError, ValueError):
        return False, "The AI advisor returned an unexpected response. Please try again.", []
