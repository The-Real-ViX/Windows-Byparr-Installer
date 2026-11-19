import time

import httpx
import pytest

from radarr_releases import RadarrReleaseClient


def _response(method, url, payload, status=200):
    request = httpx.Request(method, url)
    return httpx.Response(status, json=payload, request=request)


def test_movie_search_returns_safe_handles_and_fields(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return _response(method, url, [{
            "id": 12, "title": "Example Movie", "year": 2026,
            "hasFile": False, "monitored": True,
        }])

    monkeypatch.setattr(httpx, "request", fake_request)
    client = RadarrReleaseClient("http://127.0.0.1:7878", "secret")
    results = client.search_movies("Example")
    assert captured["method"] == "GET"
    assert captured["url"] == "http://127.0.0.1:7878/api/v3/movie"
    assert captured["params"] == {"term": "Example"}
    assert captured["headers"] == {"X-Api-Key": "secret"}
    assert results[0]["title"] == "Example Movie"
    assert results[0]["year"] == 2026
    assert len(results[0]["movie_handle"]) >= 20
    assert "id" not in results[0]
    assert "secret" not in str(results)


def test_release_search_and_grab_submit_only_selected_radarr_identity(monkeypatch):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "GET" and url.endswith("/movie"):
            return _response(method, url, [{"id": 12, "title": "Example Movie"}])
        if method == "GET" and url.endswith("/release"):
            return _response(method, url, [
                {
                    "guid": "chosen-guid", "indexerId": 4,
                    "title": "Example.Movie.1080p", "size": 123456,
                    "indexer": "Indexer A", "protocol": "torrent", "seeders": 42,
                    "quality": {"quality": {"name": "Bluray-1080p"}},
                    "approved": True, "rejections": [],
                    "downloadUrl": "https://private.example/secret",
                },
                {
                    "guid": "other-guid", "indexerId": 5,
                    "title": "Example.Movie.2160p", "approved": True,
                },
            ])
        return _response(method, url, {})

    monkeypatch.setattr(httpx, "request", fake_request)
    client = RadarrReleaseClient("http://127.0.0.1:7878", "secret")
    movie = client.search_movies("Example")[0]
    releases = client.search_releases(movie["movie_handle"])
    assert len(releases) == 2
    chosen = releases[0]
    assert chosen["quality"] == "Bluray-1080p"
    assert chosen["seeders"] == 42
    assert "downloadUrl" not in str(chosen)

    # Search and selection are read-only. Only this explicit call submits a grab.
    assert len(calls) == 2
    client.grab_release(chosen["release_handle"])
    assert len(calls) == 3
    method, url, kwargs = calls[-1]
    assert method == "POST"
    assert url.endswith("/api/v3/release")
    assert kwargs["json"] == {"guid": "chosen-guid", "indexerId": 4}
    assert kwargs["headers"] == {"X-Api-Key": "secret"}


def test_movie_search_validates_query_and_address(monkeypatch):
    client = RadarrReleaseClient("http://user:pass@127.0.0.1:7878", "key")
    with pytest.raises(ValueError, match="Invalid Radarr address"):
        client.search_movies("Example")

    client = RadarrReleaseClient("http://127.0.0.1:7878", "key")
    with pytest.raises(ValueError, match="movie title"):
        client.search_movies("  ")


def test_handles_are_single_use_and_expire(monkeypatch):
    def fake_request(method, url, **kwargs):
        return _response(method, url, [{"id": 7, "title": "Example"}])

    monkeypatch.setattr(httpx, "request", fake_request)
    client = RadarrReleaseClient("http://127.0.0.1:7878", "key")
    result = client.search_movies("Example")[0]
    client._movies[result["movie_handle"]]["expires"] = time.monotonic() - 1
    with pytest.raises(ValueError, match="expired"):
        client.search_releases(result["movie_handle"])


def test_bad_credentials_are_reported_without_submitting(monkeypatch):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(method)
        return _response(method, url, {}, status=401)

    monkeypatch.setattr(httpx, "request", fake_request)
    client = RadarrReleaseClient("http://127.0.0.1:7878", "bad-key")
    with pytest.raises(RuntimeError, match="rejected its API key"):
        client.search_movies("Example")
    assert calls == ["GET"]
