"""Manual Radarr movie and release selection.

Searches and grabs use Radarr's own API so Radarr retains control of
indexers, quality profiles and its configured download client.
"""

from __future__ import annotations

import secrets
import threading
import time

import httpx


HANDLE_TTL_SECONDS = 15 * 60
MAX_HANDLES = 500


class RadarrReleaseClient:
    """Read Radarr movie/release choices and grab only an explicitly selected release."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = str(base_url or "").rstrip("/")
        self.api_key = api_key
        self._movies: dict[str, dict] = {}
        self._releases: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _request(self, method: str, path: str, *, params=None, json=None):
        parsed = httpx.URL(self.base_url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.host
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid Radarr address.")
        if not self.api_key:
            raise RuntimeError("Radarr API key is not saved.")
        try:
            response = httpx.request(
                method,
                f"{self.base_url}/api/v3/{path.lstrip('/')}",
                params=params,
                json=json,
                headers={"X-Api-Key": self.api_key},
                timeout=30.0,
                follow_redirects=False,
                trust_env=False,
            )
            if response.status_code in (401, 403):
                raise RuntimeError("Radarr rejected its API key.")
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as error:
            raise RuntimeError("Radarr did not respond before the request timed out.") from error
        except httpx.HTTPError as error:
            raise RuntimeError("Could not complete the request to Radarr.") from error
        except ValueError as error:
            # Preserve JSON decoding errors as a safe, non-secret diagnostic.
            raise RuntimeError("Radarr returned an invalid response.") from error

    @staticmethod
    def _clean_text(value, limit=300):
        return "".join(char for char in str(value or "") if char.isprintable())[:limit]

    def _store_handle(self, store: dict, value: dict) -> str:
        handle = secrets.token_urlsafe(24)
        now = time.monotonic()
        with self._lock:
            for key in list(store):
                if store[key]["expires"] <= now:
                    del store[key]
            store[handle] = {"value": value, "expires": now + HANDLE_TTL_SECONDS}
            while len(store) > MAX_HANDLES:
                del store[next(iter(store))]
        return handle

    def _take_handle(self, store: dict, handle: str) -> dict:
        with self._lock:
            stored = store.pop(handle, None)
        if not stored or stored["expires"] <= time.monotonic():
            raise ValueError("This selection has expired or was already used. Search again.")
        return stored["value"]

    def search_movies(self, query: str) -> list[dict]:
        """Find movies already present in Radarr's library."""
        query = str(query or "").strip()
        if not query or len(query) > 200:
            raise ValueError("Enter a movie title (maximum 200 characters).")
        payload = self._request("GET", "movie", params={"term": query})
        if not isinstance(payload, list):
            raise RuntimeError("Radarr returned an unexpected movie list.")
        results = []
        for movie in payload[:50]:
            if not isinstance(movie, dict) or not isinstance(movie.get("id"), int):
                continue
            title = self._clean_text(movie.get("title"))
            if not title:
                continue
            movie_handle = self._store_handle(self._movies, {"movie_id": movie["id"]})
            results.append({
                "movie_handle": movie_handle,
                "title": title,
                "year": movie.get("year") if isinstance(movie.get("year"), int) else None,
                "has_file": bool(movie.get("hasFile")),
                "monitored": bool(movie.get("monitored")),
            })
        return results

    def search_releases(self, movie_handle: str) -> list[dict]:
        """Get Radarr's own interactive release results for a selected library movie."""
        movie = self._take_handle(self._movies, movie_handle)
        payload = self._request(
            "GET", "release", params={"movieId": movie["movie_id"]}
        )
        if not isinstance(payload, list):
            raise RuntimeError("Radarr returned an unexpected release list.")
        results = []
        for release in payload[:100]:
            if not isinstance(release, dict):
                continue
            guid = release.get("guid")
            indexer_id = release.get("indexerId")
            title = self._clean_text(release.get("title"), 500)
            if not isinstance(guid, str) or not guid or not isinstance(indexer_id, int) or not title:
                continue
            handle = self._store_handle(
                self._releases,
                {"guid": guid, "indexerId": indexer_id},
            )
            quality = release.get("quality")
            quality_label = ""
            if isinstance(quality, dict):
                quality_label = self._clean_text(
                    (quality.get("quality") or {}).get("name")
                    if isinstance(quality.get("quality"), dict) else "",
                    80,
                )
            results.append({
                "release_handle": handle,
                "title": title,
                "size": release.get("size") if isinstance(release.get("size"), (int, float)) else None,
                "indexer": self._clean_text(release.get("indexer"), 120),
                "protocol": self._clean_text(release.get("protocol"), 40),
                "seeders": release.get("seeders") if isinstance(release.get("seeders"), int) else None,
                "quality": quality_label,
                "approved": bool(release.get("approved", True)),
                "rejections": [
                    self._clean_text(reason, 180)
                    for reason in (release.get("rejections") or [])
                    if isinstance(reason, str)
                ][:10],
            })
        return results

    def grab_release(self, release_handle: str) -> None:
        """Grab exactly one selected Radarr release; caller must obtain user confirmation."""
        selected = self._take_handle(self._releases, release_handle)
        self._request("POST", "release", json=selected)
