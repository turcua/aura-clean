"""
Aura Financial Tracker - Vulnerable Version
Structured (JSON) logging configuration
Sprint 16: Kubernetes deployment + observability (OBS-001)

Same rationale as secure-version/logging_config.py — this is an operational
concern (container logs → stdout → cluster log aggregator), not one of the
intentional vulnerabilities, so it's implemented identically in both versions.
"""

import logging
import sys
from pythonjsonlogger import jsonlogger


def configure_json_logging(app):
    """Replaces Flask's/Werkzeug's default handlers with a JSON formatter on stdout."""
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={'asctime': 'timestamp', 'levelname': 'level', 'name': 'logger'},
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers = [handler]
    werkzeug_logger.setLevel(logging.INFO)
