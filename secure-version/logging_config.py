"""
Aura Financial Tracker - Secure Version
Structured (JSON) logging configuration
Sprint 16: Kubernetes deployment + observability (OBS-001)

Container logs go to stdout under Kubernetes — a cluster's log aggregator
(Loki, EFK, CloudWatch, etc.) expects structured lines it can parse and
index, not Flask/Werkzeug's default human-readable text. This swaps the
app's and Werkzeug's log handlers for a JSON formatter; log *content* is
unchanged, only the on-the-wire format.
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
