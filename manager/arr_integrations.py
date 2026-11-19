"""Read-only API connectivity checks for Radarr, Sonarr and Lidarr."""

from __future__ import annotations

import time

import httpx
from PySide6.QtCore import QThread, Signal


ARR_APPS = {
    "radarr": {"name": "Radarr", "default_port": 7878, "api_prefix": "/api/v3"},
    "sonarr": {"name": "Sonarr", "default_port": 8989, "api_prefix": "/api/v3"},
    "lidarr": {"name": "Lidarr", "default_port": 8686, "api_prefix": "/api/v1"},
}


def validate_arr_url(base_url: str, app_id: str) -> str:
    """Validate and normalize an Arr base URL without accepting embedded credentials."""
    if app_id not in ARR_APPS:
        raise ValueError("Choose Radarr, Sonarr or Lidarr.")
    value = str(base_url or "").strip().rstrip("/")
    try:
        parsed = httpx.URL(value)
    except (TypeError, httpx.InvalidURL) as error:
        raise ValueError("Enter a valid http:// or https:// address.") from error
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.host
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter a valid address without login details, query or fragment.")
    return value


def check_arr_connection_detailed(base_url: str, api_key: str, app_id: str):
    """Return a safe connection result, HTTP code and elapsed milliseconds."""
    started = time.perf_counter()
    if not api_key:
        return False, "API key not saved", None, 0
    status_code = None
    try:
        base_url = validate_arr_url(base_url, app_id)
        prefix = ARR_APPS[app_id]["api_prefix"]
        response = httpx.get(
            f"{base_url}{prefix}/system/status",
            headers={"X-Api-Key": api_key},
            timeout=10.0,
            follow_redirects=False,
            trust_env=False,
        )
        status_code = response.status_code
        elapsed = round((time.perf_counter() - started) * 1000)
        if status_code in (401, 403):
            return False, "API key rejected", status_code, elapsed
        if status_code != 200:
            return False, f"Connection returned HTTP {status_code}", status_code, elapsed
        payload = response.json()
        if not isinstance(payload, dict):
            return False, "Unexpected application response", status_code, elapsed
        version = "".join(c for c in str(payload.get("version") or "") if c.isprintable())[:40]
        return True, f"Connected (version {version})" if version else "Connected", status_code, elapsed
    except ValueError as error:
        return False, str(error), status_code, round((time.perf_counter() - started) * 1000)
    except (httpx.RequestError, httpx.InvalidURL):
        return False, "Could not reach the application", status_code, round((time.perf_counter() - started) * 1000)


def check_arr_connection(base_url: str, api_key: str, app_id: str) -> tuple[bool, str]:
    """Compatibility wrapper preserving the original public return shape."""
    ok, message, _status, _elapsed = check_arr_connection_detailed(base_url, api_key, app_id)
    return ok, message


class ArrIntegrationCheckWorker(QThread):
    """Run a single Arr API check without blocking the desktop interface."""

    result = Signal(str, bool, str)
    diagnostic = Signal(str, bool, object, int, str)

    def __init__(self, app_id: str, base_url: str, api_key: str, parent=None):
        super().__init__(parent)
        if app_id not in ARR_APPS:
            raise ValueError("Choose Radarr, Sonarr or Lidarr.")
        self.app_id = app_id
        self.base_url = base_url
        self.api_key = api_key

    def run(self):
        ok, message, status_code, elapsed_ms = check_arr_connection_detailed(
            self.base_url, self.api_key, self.app_id
        )
        self.result.emit(self.app_id, ok, message)
        self.diagnostic.emit(self.app_id, ok, status_code, elapsed_ms, message)
