"""Read-only API connectivity checks for Radarr, Sonarr and Lidarr."""

from __future__ import annotations

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


def check_arr_connection(base_url: str, api_key: str, app_id: str) -> tuple[bool, str]:
    """Perform a read-only Arr system/status request and return a safe summary."""
    if not api_key:
        return False, "API key not saved"
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
        if response.status_code in (401, 403):
            return False, "API key rejected"
        if response.status_code != 200:
            return False, f"Connection returned HTTP {response.status_code}"
        payload = response.json()
        if not isinstance(payload, dict):
            return False, "Unexpected application response"
        version = str(payload.get("version") or "").strip()
        if version:
            return True, f"Connected (version {version[:40]})"
        return True, "Connected"
    except ValueError as error:
        return False, str(error)
    except (httpx.RequestError, httpx.InvalidURL):
        return False, "Could not reach the application"


class ArrIntegrationCheckWorker(QThread):
    """Run a single Arr API check without blocking the desktop interface."""

    result = Signal(str, bool, str)

    def __init__(self, app_id: str, base_url: str, api_key: str, parent=None):
        super().__init__(parent)
        if app_id not in ARR_APPS:
            raise ValueError("Choose Radarr, Sonarr or Lidarr.")
        self.app_id = app_id
        self.base_url = base_url
        self.api_key = api_key

    def run(self):
        ok, message = check_arr_connection(self.base_url, self.api_key, self.app_id)
        self.result.emit(self.app_id, ok, message)
