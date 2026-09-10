"""
Aura Financial Tracker - Secure Version
Shared extension instances
Sprint 15: Security Hardening & Audit

Kept in their own module (rather than instantiated directly in app.py) so
routes/auth.py can import and decorate with `limiter` without a circular
import — app.py still owns the actual init_app() binding.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
