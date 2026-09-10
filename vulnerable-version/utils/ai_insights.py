"""
Aura Financial Tracker - Vulnerable Version
AI Insight Narration (WITH INTENTIONAL VULNERABILITIES)
Sprint 25: Proactive Insights

VULNERABILITY: the findings prompt is built via naive string concatenation,
same pattern as utils/ai_context.py — no delimiter, no "treat as data"
framing. Category names and recurring-transaction descriptions embedded in
the findings (both user-controlled elsewhere in this app) flow straight
into the same text as the instructions, inheriting the same indirect
prompt injection surface already confirmed in Sprint 24 (VULN-077), now
reachable via this second call site too.
"""

from datetime import date

from models.transaction import Transaction
from models.recurring_transaction import RecurringTransaction
from models.savings_goal import SavingsGoal
from utils.groq_client import send_chat_completion


def _goal_pacing(goals):
    findings = []
    today = date.today()
    for g in goals:
        if not g.target_date or not g.target_amount:
            continue
        remaining = float(g.target_amount) - float(g.current_amount or 0)
        if remaining <= 0:
            continue
        days_left = (g.target_date - today).days
        if days_left <= 0:
            continue
        months_left = max(days_left / 30.0, 0.1)
        required_monthly = remaining / months_left
        monthly_target = float(g.monthly_target or 0)
        if monthly_target > 0 and required_monthly > monthly_target * 1.1:
            findings.append({
                'goal': g.name,
                'remaining': round(remaining, 2),
                'target_date': str(g.target_date),
                'required_monthly': round(required_monthly, 2),
                'current_monthly_target': round(monthly_target, 2),
            })
    return findings


def build_findings(mysql, user_id):
    """Returns (findings dict, has_findings bool)."""
    anomalies = Transaction.get_monthly_anomalies(mysql, user_id)
    cost_creep = RecurringTransaction.get_cost_creep(mysql, user_id)
    goals = SavingsGoal.get_all_by_user(mysql, user_id)
    off_pace_goals = _goal_pacing(goals)

    findings = {
        'anomalies': anomalies,
        'cost_creep': cost_creep,
        'off_pace_goals': off_pace_goals,
    }
    has_findings = bool(anomalies or cost_creep or off_pace_goals)
    return findings, has_findings


def narrate_findings(api_key, model, findings):
    """Returns the narrated message string, or None on failure."""
    # VULN: naive string concatenation, no delimiter between instructions
    # and data — same pattern as utils/ai_context.py
    prompt = "You are Solis, Aura's AI financial advisor. Write a short proactive insight message based on this data: "

    for a in findings['anomalies']:
        prompt += f"Spending anomaly in {a['category']}: {a['current']} this month vs {a['average']} average ({a['pct_above']}% above). "
    for c in findings['cost_creep']:
        prompt += f"Recurring cost increase for {c['description']}: was {c['first_amount']}, now {c['current_amount']} ({c['pct_increase']}% increase). "
    for g in findings['off_pace_goals']:
        prompt += f"Goal {g['goal']} is behind pace: needs {g['required_monthly']}/month, currently targeting {g['current_monthly_target']}/month. "

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Write the proactive insight message now."},
    ]
    success, content, _ = send_chat_completion(api_key, model, messages)
    return content if success else None
