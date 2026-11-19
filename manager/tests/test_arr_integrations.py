import httpx

from arr_integrations import ARR_APPS, check_arr_connection, check_arr_connection_detailed, validate_arr_url


def test_arr_app_api_prefixes_and_default_ports():
    assert ARR_APPS["radarr"]["api_prefix"] == "/api/v3"
    assert ARR_APPS["sonarr"]["default_port"] == 8989
    assert ARR_APPS["lidarr"]["api_prefix"] == "/api/v1"


def test_validate_arr_url_normalizes_trailing_slash():
    assert validate_arr_url("http://127.0.0.1:7878/", "radarr") == "http://127.0.0.1:7878"


def test_validate_arr_url_rejects_credentials_and_query():
    for value in (
        "http://user:pass@127.0.0.1:7878",
        "http://127.0.0.1:7878?apiKey=secret",
        "ftp://127.0.0.1:7878",
    ):
        try:
            validate_arr_url(value, "radarr")
        except ValueError:
            pass
        else:
            raise AssertionError(f"URL should have been rejected: {value}")


def test_check_arr_connection_uses_read_only_status_endpoint(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"version": "5.0.0"}

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(httpx, "get", fake_get)
    assert check_arr_connection("http://127.0.0.1:7878", "test-key", "radarr") == (
        True,
        "Connected (version 5.0.0)",
    )
    url, kwargs = calls[0]
    assert url == "http://127.0.0.1:7878/api/v3/system/status"
    assert kwargs["headers"] == {"X-Api-Key": "test-key"}
    assert kwargs["follow_redirects"] is False
    assert kwargs["trust_env"] is False


def test_check_arr_connection_never_reports_api_key(monkeypatch):
    class Response:
        status_code = 401

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: Response())
    ok, message = check_arr_connection("http://127.0.0.1:8989", "secret-key", "sonarr")
    assert not ok
    assert message == "API key rejected"
    assert "secret-key" not in message


def test_check_arr_connection_handles_unreachable_service(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("private details")

    monkeypatch.setattr(httpx, "get", fail)
    assert check_arr_connection("http://127.0.0.1:8686", "key", "lidarr") == (
        False,
        "Could not reach the application",
    )


def test_detailed_arr_check_reports_http_status_and_duration(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {"version": "6.4.4"}

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: Response())
    ok, message, status_code, elapsed_ms = check_arr_connection_detailed(
        "http://127.0.0.1:7878", "key", "radarr"
    )
    assert ok
    assert message == "Connected (version 6.4.4)"
    assert status_code == 200
    assert elapsed_ms >= 0
