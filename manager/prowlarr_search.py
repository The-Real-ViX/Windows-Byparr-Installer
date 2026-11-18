"""Read-only search access to a configured Prowlarr instance."""

import httpx


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
            results.append({
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
            })
        return results
