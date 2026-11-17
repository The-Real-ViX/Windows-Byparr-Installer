"""Read-only Prowlarr and qBittorrent integration diagnostics."""

import httpx
from PySide6.QtCore import QThread, Signal


class ProwlarrIntegrationCheckWorker(QThread):
    """Verify Prowlarr API access and test its configured qBittorrent client."""

    result = Signal(bool, str, bool, str)

    def __init__(self, base_url: str, api_key: str, parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _emit(self, prowlarr_ok, prowlarr_message, qbittorrent_ok, qbittorrent_message):
        self.result.emit(prowlarr_ok, prowlarr_message, qbittorrent_ok, qbittorrent_message)

    def run(self):
        if not self.api_key:
            self._emit(False, "API key not saved", False, "Not checked")
            return

        try:
            parsed = httpx.URL(self.base_url)
            if parsed.scheme not in ("http", "https") or not parsed.host:
                self._emit(False, "Enter a valid Prowlarr address", False, "Not checked")
                return

            headers = {"X-Api-Key": self.api_key}
            clients_response = httpx.get(
                f"{self.base_url}/api/v1/downloadclient",
                headers=headers,
                timeout=10.0,
            )
            if clients_response.status_code in (401, 403):
                self._emit(False, "API key rejected", False, "Not checked")
                return
            if clients_response.status_code != 200:
                self._emit(
                    False,
                    f"Connection returned HTTP {clients_response.status_code}",
                    False,
                    "Not checked",
                )
                return

            clients = clients_response.json()
            if not isinstance(clients, list):
                self._emit(False, "Unexpected Prowlarr response", False, "Not checked")
                return

            qbittorrent_clients = [
                client for client in clients
                if "qbittorrent" in " ".join(
                    str(client.get(field) or "")
                    for field in ("implementation", "implementationName", "name")
                ).lower()
            ]
            if not qbittorrent_clients:
                self._emit(True, "Connected", False, "Not configured in Prowlarr")
                return

            enabled_clients = [client for client in qbittorrent_clients if client.get("enable")]
            if not enabled_clients:
                self._emit(True, "Connected", False, "Configured but disabled")
                return

            response = httpx.post(
                f"{self.base_url}/api/v1/downloadclient/testall",
                headers=headers,
                timeout=30.0,
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
                if not failures:
                    self._emit(True, "Connected", True, "Connection test passed")
                else:
                    self._emit(
                        True, "Connected", False,
                        "Connection test failed — check Prowlarr"
                    )
                return

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

        except (httpx.RequestError, httpx.InvalidURL, ValueError):
            self._emit(False, "Could not reach Prowlarr", False, "Not checked")
