"""Read-only Prowlarr and qBittorrent integration diagnostics."""

import time

import httpx
from PySide6.QtCore import QThread, Signal


class ProwlarrIntegrationCheckWorker(QThread):
    """Verify Prowlarr API access and test its configured qBittorrent client."""

    result = Signal(bool, str, bool, str)
    diagnostic = Signal(str, bool, object, int, str)

    def __init__(self, base_url: str, api_key: str, parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _emit(self, prowlarr_ok, prowlarr_message, qbittorrent_ok, qbittorrent_message):
        self.result.emit(prowlarr_ok, prowlarr_message, qbittorrent_ok, qbittorrent_message)

    def run(self):
        if not self.api_key:
            self._emit(False, "API key not saved", False, "Not checked")
            self.diagnostic.emit("Prowlarr", False, None, 0, "API key not saved")
            self.diagnostic.emit("qBittorrent (via Prowlarr)", False, None, 0, "Not checked")
            return

        try:
            parsed = httpx.URL(self.base_url)
            if (
                parsed.scheme not in ("http", "https") or not parsed.host
                or parsed.username or parsed.password or parsed.query or parsed.fragment
            ):
                self._emit(False, "Enter a valid Prowlarr address", False, "Not checked")
                self.diagnostic.emit("Prowlarr", False, None, 0, "Invalid Prowlarr address")
                return

            headers = {"X-Api-Key": self.api_key}
            started = time.perf_counter()
            clients_response = httpx.get(
                f"{self.base_url}/api/v1/downloadclient",
                headers=headers,
                timeout=10.0,
                follow_redirects=False,
                trust_env=False,
            )
            prowlarr_status = clients_response.status_code
            prowlarr_elapsed = round((time.perf_counter() - started) * 1000)
            if prowlarr_status in (401, 403):
                self.diagnostic.emit("Prowlarr", False, prowlarr_status, prowlarr_elapsed, "API key rejected")
                self._emit(False, "API key rejected", False, "Not checked")
                return
            if prowlarr_status != 200:
                self.diagnostic.emit("Prowlarr", False, prowlarr_status, prowlarr_elapsed, "Unexpected API response")
                self._emit(False, f"Connection returned HTTP {prowlarr_status}", False, "Not checked")
                return

            clients = clients_response.json()
            if not isinstance(clients, list):
                self.diagnostic.emit("Prowlarr", False, prowlarr_status, prowlarr_elapsed, "Unexpected application response")
                self._emit(False, "Unexpected Prowlarr response", False, "Not checked")
                return
            self.diagnostic.emit("Prowlarr", True, prowlarr_status, prowlarr_elapsed, "Connected")

            qbittorrent_clients = [
                client for client in clients
                if "qbittorrent" in " ".join(
                    str(client.get(field) or "")
                    for field in ("implementation", "implementationName", "name")
                ).lower()
            ]
            if not qbittorrent_clients:
                self._emit(True, "Connected", False, "Not configured in Prowlarr")
                self.diagnostic.emit("qBittorrent (via Prowlarr)", False, None, 0, "Not configured in Prowlarr")
                return

            enabled_clients = [client for client in qbittorrent_clients if client.get("enable")]
            if not enabled_clients:
                self._emit(True, "Connected", False, "Configured but disabled")
                self.diagnostic.emit("qBittorrent (via Prowlarr)", False, None, 0, "Configured but disabled")
                return

            started = time.perf_counter()
            response = httpx.post(
                f"{self.base_url}/api/v1/downloadclient/testall",
                headers=headers,
                timeout=30.0,
                follow_redirects=False,
                trust_env=False,
            )
            try:
                test_results = response.json()
            except ValueError:
                test_results = []

            if not isinstance(test_results, list):
                test_results = []

            for client in enabled_clients:
                test_result = next(
                    (
                        item for item in test_results
                        if isinstance(item, dict) and item.get("id") == client.get("id")
                    ),
                    None,
                )
                if test_result is None:
                    continue

                failures = test_result.get("validationFailures") or []
                if response.status_code == 200 and not failures:
                    elapsed = round((time.perf_counter() - started) * 1000)
                    self.diagnostic.emit("qBittorrent (via Prowlarr)", True, response.status_code, elapsed, "Connection test passed")
                    self._emit(True, "Connected", True, "Connection test passed")
                else:
                    elapsed = round((time.perf_counter() - started) * 1000)
                    self.diagnostic.emit("qBittorrent (via Prowlarr)", False, response.status_code, elapsed, "Connection test failed")
                    self._emit(True, "Connected", False, "Connection test failed — check Prowlarr")
                return

            elapsed = round((time.perf_counter() - started) * 1000)
            test_ok = response.status_code == 200
            self.diagnostic.emit(
                "qBittorrent (via Prowlarr)", test_ok, response.status_code,
                elapsed, "Test result unavailable" if test_ok else "Download-client test returned an error",
            )
            if response.status_code == 200:
                self._emit(True, "Connected", False, "Test result unavailable")
            elif response.status_code == 400:
                self._emit(True, "Connected", False, "One or more client tests failed")
            else:
                self._emit(
                    True,
                    "Connected",
                    False,
                    f"Client test returned HTTP {response.status_code}",
                )

        except httpx.TimeoutException:
            self.diagnostic.emit("Prowlarr / qBittorrent", False, None, 0, "API request timed out")
            self._emit(False, "Could not reach Prowlarr", False, "Not checked")
        except (httpx.RequestError, httpx.InvalidURL, ValueError):
            self.diagnostic.emit("Prowlarr / qBittorrent", False, None, 0, "API request failed")
            self._emit(False, "Could not reach Prowlarr", False, "Not checked")
