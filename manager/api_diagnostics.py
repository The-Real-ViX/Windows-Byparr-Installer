"""Consistent, credential-safe API diagnostic log formatting."""

from __future__ import annotations

import re
from datetime import datetime


def format_api_diagnostic(service, success, status_code, elapsed_ms, detail):
    """Format one API check without recording addresses, request data or secrets."""
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    safe_service = re.sub(r"[^A-Za-z0-9 ()/+_-]", "", str(service))[:64] or "API"
    safe_detail = "".join(
        " " if c in "\r\n" else c
        for c in str(detail) if c.isprintable() or c in "\r\n"
    )
    safe_detail = re.sub(
        r"(?i)(api[ _-]?key|password|token|secret|cookie)(\s*[:=]\s*)\S+",
        r"\1\2[REDACTED]", safe_detail,
    )[:180]
    http_status = f"HTTP {int(status_code)}" if status_code is not None else "HTTP n/a"
    duration = max(0, min(int(elapsed_ms), 600_000))
    outcome = "PASS" if success else "FAIL"
    return f"[{timestamp}] API CHECK | {safe_service} | {outcome} | {http_status} | {duration} ms | {safe_detail}"
