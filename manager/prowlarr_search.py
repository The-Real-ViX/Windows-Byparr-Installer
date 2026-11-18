"""Read-only search access to a configured Prowlarr instance."""

import secrets
import time
import threading

import httpx


RELEASE_HANDLE_SECONDS = 30 * 60

SEARCH_CATEGORIES = {
    "all": {"label": "All", "type": "search", "category": None},
    "movies": {"label": "Movies", "type": "movie", "category": 2000},
    "tv": {"label": "TV Shows", "type": "tvsearch", "category": 5000},
    "audio": {"label": "Audio / Music", "type": "music", "category": 3000},
    "books": {"label": "Books", "type": "book", "category": 7000},
    "pc": {"label": "PC", "type": "search", "category": 4000},
    "console": {"label": "Console", "type": "search", "category": 1000},
}


class ProwlarrSearchClient:
    """Execute a text search and return a small, safe release summary."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._releases = {}
        self._releases_lock = threading.Lock()

    @staticmethod
    def _size_label(value):
        try:
            size = int(value)
        except (TypeError, ValueError):
            return "Size unknown"
        if size < 0:
            return "Size unknown"
        units = ("B", "KB", "MB", "GB", "TB")
        amount = float(size)
        for unit in units:
            if amount < 1024 or unit == units[-1]:
                return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
            amount /= 1024
        return "Size unknown"

    def search(self, query: str, category: str = "all") -> list[dict]:
        """Search configured indexers using a safe Prowlarr search mode/category."""
        parsed = httpx.URL(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.host:
            raise ValueError("Invalid Prowlarr address.")
        search_category = SEARCH_CATEGORIES.get(category)
        if search_category is None:
            raise ValueError("Choose a valid search category.")
        params = [
            ("query", query),
            ("type", search_category["type"]),
            ("limit", 50),
        ]
        if search_category["category"] is not None:
            params.append(("categories", search_category["category"]))
        try:
            response = httpx.get(
                f"{self.base_url}/api/v1/search",
                params=params,
                headers={"X-Api-Key": self.api_key},
                timeout=180.0,
            )
            if response.status_code in (401, 403):
                raise RuntimeError("Prowlarr rejected its API key.")
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as error:
            raise RuntimeError(
                "Prowlarr search timed out after 180 seconds. Check the indexers and try again."
            ) from error
        except httpx.HTTPError as error:
            raise RuntimeError("Could not retrieve Prowlarr search results.") from error
        if not isinstance(payload, list):
            raise TypeError("Unexpected Prowlarr search response.")
        results = []
        for item in payload[:50]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            grab_id = None
            if item.get("guid") and isinstance(item.get("indexerId"), int):
                grab_id = secrets.token_urlsafe(24)
                now = time.monotonic()
                with self._releases_lock:
                    self._releases = {
                        key: value for key, value in self._releases.items()
                        if value["expires"] > now
                    }
                    self._releases[grab_id] = {
                        "release": dict(item),
                        "expires": now + RELEASE_HANDLE_SECONDS,
                    }
                    if len(self._releases) > 500:
                        self._releases.pop(next(iter(self._releases)))
            result = {
                "title": title[:500],
                "indexer": str(
                    item.get("indexer") or item.get("indexerName") or "Unknown indexer"
                )[:120],
                "size_label": self._size_label(item.get("size")),
                "seeders": (
                    item.get("seeders")
                    if isinstance(item.get("seeders"), int) else None
                ),
                "leechers": (
                    item.get("leechers")
                    if isinstance(item.get("leechers"), int) else None
                ),
                "protocol": str(item.get("protocol") or "")[:40],
                "publish_date": str(item.get("publishDate") or "")[:40],
            }
            if grab_id:
                result["grab_id"] = grab_id
            results.append(result)
        return results

    def grab(self, grab_id: str) -> None:
        """Ask Prowlarr to send a previously returned release to its configured download client."""
        with self._releases_lock:
            stored = self._releases.get(grab_id)
            if not stored or stored["expires"] <= time.monotonic():
                self._releases.pop(grab_id, None)
                raise ValueError("This search result has expired. Run the search again.")
            release = stored["release"]
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/search",
                json=release,
                headers={"X-Api-Key": self.api_key},
                timeout=30.0,
            )
            if response.status_code in (401, 403):
                raise RuntimeError("Prowlarr rejected its API key.")
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise RuntimeError("Prowlarr did not confirm the grab before timing out.") from error
        except httpx.HTTPError as error:
            raise RuntimeError("Prowlarr could not send this release to its download client.") from error
