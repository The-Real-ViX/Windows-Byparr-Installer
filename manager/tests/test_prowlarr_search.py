import httpx
import pytest

from prowlarr_search import ProwlarrSearchClient


def test_search_uses_api_key_header_and_returns_safe_release_fields(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(200, json=[{
            "title": "Example.Release.1080p",
            "indexer": "Example Indexer",
            "size": 1073741824,
            "seeders": 42,
            "leechers": 3,
            "protocol": "torrent",
            "downloadUrl": "https://private.example/download?apikey=secret",
            "magnetUrl": "magnet:?xt=secret",
        }], request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    result = ProwlarrSearchClient("http://127.0.0.1:9696", "secret-key").search("example")
    assert captured["headers"] == {"X-Api-Key": "secret-key"}
    assert captured["params"] == {"query": "example", "type": "search", "limit": 50}
    assert result == [{
        "title": "Example.Release.1080p",
        "indexer": "Example Indexer",
        "size_label": "1.0 GB",
        "seeders": 42,
        "leechers": 3,
        "protocol": "torrent",
        "publish_date": "",
    }]
    assert "downloadUrl" not in result[0]
    assert "secret-key" not in str(result)


def test_search_rejects_non_list_response(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(200, json={"error": "bad"}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(ValueError, match="Unexpected"):
        ProwlarrSearchClient("http://127.0.0.1:9696", "key").search("example")


def test_search_reports_rejected_api_key(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(401, json={}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(RuntimeError, match="API key"):
        ProwlarrSearchClient("http://127.0.0.1:9696", "key").search("example")
