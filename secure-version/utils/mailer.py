"""
Aura Financial Tracker - Secure Version
Mail sending utility (Sprint 52, ENH-03)

Plain smtplib — no new dependency needed for this. Identical in both app
versions (not a vulnerable/secure contrast point): the intentional weakness
for ENH-03 lives in how the reset token is generated (models/user.py), not
in how the email carrying it gets sent.
"""

import smtplib
from email.mime.text import MIMEText
from flask import current_app


def send_email(to_address, subject, body):
    """
    Sends a plain-text email via the configured SMTP server.
    Returns (success, error_message) — a mail-server outage or missing
    config is reported back rather than raised, so it never 500s a request
    that otherwise handled everything correctly.
    """
    config = current_app.config
    if not config.get('MAIL_USERNAME') or not config.get('MAIL_PASSWORD'):
        return False, "Email is not configured on this server"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config['MAIL_DEFAULT_SENDER']
    msg['To'] = to_address

    try:
        with smtplib.SMTP(config['MAIL_SERVER'], config['MAIL_PORT']) as server:
            if config.get('MAIL_USE_TLS'):
                server.starttls()
            server.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
            server.sendmail(config['MAIL_DEFAULT_SENDER'], [to_address], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)
