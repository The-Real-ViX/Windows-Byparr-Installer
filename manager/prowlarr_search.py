"""Read-only search access to a configured Prowlarr instance."""

import httpx


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

    def search(self, query: str) -> list[dict]:
        """Search all configured indexers; never return download URLs or API keys."""
        parsed = httpx.URL(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.host:
            raise ValueError("Invalid Prowlarr address.")
        response = httpx.get(
            f"{self.base_url}/api/v1/search",
            params={"query": query, "type": "search", "limit": 50},
            headers={"X-Api-Key": self.api_key},
            timeout=90.0,
        )
        if response.status_code in (401, 403):
            raise RuntimeError("Prowlarr rejected its API key.")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unexpected Prowlarr search response.")
        results = []
        for item in payload[:50]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            results.append({
                "title": title[:500],
                "indexer": str(item.get("indexer") or item.get("indexerName") or "Unknown indexer")[:120],
                "size_label": self._size_label(item.get("size")),
                "seeders": item.get("seeders") if isinstance(item.get("seeders"), int) else None,
                "leechers": item.get("leechers") if isinstance(item.get("leechers"), int) else None,
                "protocol": str(item.get("protocol") or "")[:40],
                "publish_date": str(item.get("publishDate") or "")[:40],
            })
        return results
