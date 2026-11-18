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
            "guid": "example-guid",
            "indexerId": 7,
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
    assert captured["params"] == [
        ("query", "example"), ("type", "search"), ("limit", 50)
    ]
    assert captured["timeout"] == 180.0
    assert len(result) == 1
    assert len(result[0]["grab_id"]) >= 20
    assert {key: value for key, value in result[0].items() if key != "grab_id"} == {
        "title": "Example.Release.1080p",
        "indexer": "Example Indexer",
        "size_label": "1.0 GB",
        "seeders": 42,
        "leechers": 3,
        "protocol": "torrent",
        "publish_date": "",
    }
    assert "downloadUrl" not in result[0]
    assert "secret-key" not in str(result)


@pytest.mark.parametrize(
    ("category", "expected_type", "expected_category"),
    [
        ("movies", "movie", 2000),
        ("tv", "tvsearch", 5000),
        ("audio", "music", 3000),
        ("books", "book", 7000),
        ("pc", "search", 4000),
        ("console", "search", 1000),
    ],
)
def test_search_maps_categories_to_prowlarr_modes(monkeypatch, category, expected_type, expected_category):
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return httpx.Response(200, json=[], request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    ProwlarrSearchClient("http://127.0.0.1:9696", "key").search("example", category)
    assert ("type", expected_type) in captured["params"]
    assert ("categories", expected_category) in captured["params"]


def test_search_rejects_unknown_category():
    with pytest.raises(ValueError, match="category"):
        ProwlarrSearchClient("http://127.0.0.1:9696", "key").search("example", "unknown")


def test_search_rejects_non_list_response(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(200, json={"error": "bad"}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(TypeError, match="Unexpected"):
        ProwlarrSearchClient("http://127.0.0.1:9696", "key").search("example")


def test_search_reports_rejected_api_key(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(401, json={}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(RuntimeError, match="API key"):
        ProwlarrSearchClient("http://127.0.0.1:9696", "key").search("example")



def test_search_reports_timeout_clearly(monkeypatch):
    def fake_get(url, **kwargs):
        raise httpx.ReadTimeout("request timed out")

    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(RuntimeError, match="timed out after 180 seconds"):
        ProwlarrSearchClient("http://127.0.0.1:9696", "key").search("example")

def test_grab_posts_selected_release_to_prowlarr_download_client(monkeypatch):
    captured = {}
    release = {"guid": "release-guid", "indexerId": 12, "title": "Example.Release"}

    def fake_get(url, **kwargs):
        return httpx.Response(200, json=[release], request=httpx.Request("GET", url))

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(200, json={}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)
    client = ProwlarrSearchClient("http://127.0.0.1:9696", "secret-key")
    results = client.search("example")
    client.grab(results[0]["grab_id"])
    assert captured["url"] == "http://127.0.0.1:9696/api/v1/search"
    assert captured["json"] == release
    assert captured["headers"] == {"X-Api-Key": "secret-key"}
    assert captured["timeout"] == 30.0


def test_grab_rejects_expired_or_unknown_result():
    client = ProwlarrSearchClient("http://127.0.0.1:9696", "key")
    with pytest.raises(ValueError, match="expired"):
        client.grab("unknown-result-handle")
