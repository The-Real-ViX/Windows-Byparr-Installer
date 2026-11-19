import pytest

from remote_access import (
    password_verifier,
    validate_tailscale_binding,
    verify_password,
)


@pytest.mark.parametrize(
    ("host", "port", "expected"),
    [
        ("100.101.20.30", "8765", ("100.101.20.30", 8765)),
        ("fd7a:115c:a1e0::1234", 8765, ("fd7a:115c:a1e0::1234", 8765)),
    ],
)
def test_accepts_tailscale_addresses(host, port, expected):
    assert validate_tailscale_binding(host, port) == expected


@pytest.mark.parametrize("host", ["127.0.0.1", "192.168.1.20", "8.8.8.8", "example.com"])
def test_rejects_non_tailscale_addresses(host):
    with pytest.raises(ValueError, match="Tailscale"):
        validate_tailscale_binding(host, 8765)


def test_rejects_invalid_ports():
    for port in (0, 65536, "not-a-port"):
        with pytest.raises(ValueError):
            validate_tailscale_binding("100.100.10.1", port)


def test_password_verifier_is_salted_and_verifiable():
    password = "a-long-test-password-123!"
    salt, verifier = password_verifier(password)
    assert verify_password(password, salt, verifier)
    assert not verify_password("incorrect-password", salt, verifier)
    other_salt, other_verifier = password_verifier(password)
    assert salt != other_salt
    assert verifier != other_verifier


def test_password_policy_rejects_short_password():
    with pytest.raises(ValueError, match="14 characters"):
        password_verifier("too-short")


def test_password_policy_rejects_oversized_password():
    with pytest.raises(ValueError, match="1024 characters"):
        password_verifier("x" * 1025)


def test_remote_log_redaction_masks_common_secrets():
    from remote_access import redact_log_line

    line = "api_key=abc123 password:hello token=xyz cookie=session123"
    result = redact_log_line(line)
    assert "abc123" not in result
    assert "hello" not in result
    assert "xyz" not in result
    assert "session123" not in result
    assert result.count("[REDACTED]") == 4

    from remote_access import redact_log_line

    sensitive = redact_log_line(
        "Authorization: Bearer abc123 https://user:pass@example.test/path "
        "https://host.test/api?apikey=secret&token=private"
    )
    for secret in ("abc123", "pass@", "secret", "private"):
        assert secret not in sensitive



def test_remote_audit_events_are_sent_to_manager_log():
    from remote_access import RemoteDashboardServer

    events = []
    server = RemoteDashboardServer(
        "100.101.20.30", 8765, "test-user", "00" * 16, "11" * 32,
        lambda: {}, lambda _action: None, audit_logger=events.append,
    )
    server.audit("Login successful for user 'test-user' from 100.101.20.30.")
    assert events == [
        "[REMOTE ACCESS] Login successful for user 'test-user' from 100.101.20.30."
    ]


def test_remote_audit_failure_does_not_break_dashboard():
    from remote_access import RemoteDashboardServer

    def broken_logger(_message):
        raise RuntimeError("log unavailable")

    server = RemoteDashboardServer(
        "100.101.20.30", 8765, "test-user", "00" * 16, "11" * 32,
        lambda: {}, lambda _action: None, audit_logger=broken_logger,
    )
    server.audit("Login successful")


def test_dashboard_script_uses_valid_newline_expression():
    from remote_access import DASHBOARD

    assert ".join(String.fromCharCode(10))" in DASHBOARD
    assert "Live status updated:" in DASHBOARD
    assert "setInterval(refresh,5000)" in DASHBOARD
    assert "searchInFlight" in DASHBOARD
    assert "button.disabled=true" in DASHBOARD
    assert "button.disabled=false" in DASHBOARD
    assert "search-spinner" in DASHBOARD
    assert "elapsedSearchSeconds()" in DASHBOARD
    assert "Keep this page open." in DASHBOARD



def test_remote_dashboard_contains_prowlarr_search_panel():
    from remote_access import DASHBOARD

    assert "Prowlarr Search" in DASHBOARD
    assert 'id="radarr"' in DASHBOARD
    assert 'id="sonarr"' in DASHBOARD
    assert 'id="lidarr"' in DASHBOARD
    assert "d.radarr||'Not configured'" in DASHBOARD
    assert "d.sonarr||'Not configured'" in DASHBOARD
    assert "d.lidarr||'Not configured'" in DASHBOARD
    assert "search-form" in DASHBOARD
    assert 'id="clear-search"' in DASHBOARD
    assert "Search cleared. Enter a new search when ready." in DASHBOARD
    assert "clearButton.disabled=true" in DASHBOARD
    assert 'id="search-category"' in DASHBOARD
    assert 'value="movies"' in DASHBOARD
    assert 'value="tv"' in DASHBOARD
    assert 'value="audio"' in DASHBOARD
    assert 'value="pc"' in DASHBOARD
    assert "JSON.stringify({query,category})" in DASHBOARD
    assert "fetch('/api/search'" in DASHBOARD
    assert "renderSearchResults" in DASHBOARD
    assert "Send to qBittorrent" in DASHBOARD
    assert "window.confirm" in DASHBOARD
    assert "nonce=\"__CSP_NONCE__\"" in DASHBOARD
    assert "onclick=" not in DASHBOARD
    assert 'addEventListener("click",()=>act(action))' in DASHBOARD


def test_remote_grab_handler_is_optional_and_callable():
    from remote_access import RemoteDashboardServer

    grabbed = []
    server = RemoteDashboardServer(
        "100.101.20.30", 8765, "test-user", "00" * 16, "11" * 32,
        lambda: {}, lambda _action: None, grab_handler=grabbed.append,
    )
    assert server.grab_handler is not None
    server.grab_handler("opaque-release-id")
    assert grabbed == ["opaque-release-id"]



def test_remote_request_host_and_origin_validation():
    from remote_access import validate_request_host, validate_request_origin

    assert validate_request_host("100.101.20.30:8765", "100.101.20.30", 8765)
    assert not validate_request_host("evil.example:8765", "100.101.20.30", 8765)
    assert validate_request_host("[fd7a:115c:a1e0::1234]:8765", "fd7a:115c:a1e0::1234", 8765)
    assert validate_request_origin(
        "http://100.101.20.30:8765", "100.101.20.30:8765"
    )
    assert not validate_request_origin(
        "https://100.101.20.30:8765", "100.101.20.30:8765"
    )
    assert not validate_request_origin(
        "http://evil.example:8765", "100.101.20.30:8765"
    )
    assert not validate_request_origin(
        "null", "100.101.20.30:8765"
    )


def test_password_verification_rejects_oversized_input():
    from remote_access import verify_password

    salt, verifier = password_verifier("a-long-test-password-123!")
    assert not verify_password("x" * 1025, salt, verifier)


def test_remote_username_rejects_log_injection():
    from remote_access import RemoteDashboardServer

    with pytest.raises(ValueError, match="safe characters"):
        RemoteDashboardServer(
            "100.101.20.30", 8765, "bad\\nuser", "00" * 16, "11" * 32,
            lambda: {}, lambda _action: None,
        )



def test_remote_log_redaction_masks_json_credentials():
    from remote_access import redact_log_line

    line = '{"apiKey":"api-secret","password":"pw-secret","Authorization":"Bearer auth-secret"}'
    result = redact_log_line(line)
    for secret in ("api-secret", "pw-secret", "auth-secret"):
        assert secret not in result
    assert result.count("[REDACTED]") >= 3


def test_password_verification_rejects_invalid_unicode():
    from remote_access import verify_password

    salt, verifier = password_verifier("a-long-test-password-123!")
    assert not verify_password("\ud800", salt, verifier)


def test_release_grab_handle_is_single_use(monkeypatch):
    import time
    import httpx
    from prowlarr_search import ProwlarrSearchClient

    client = ProwlarrSearchClient("http://127.0.0.1:9696", "test-api-key")
    client._releases["opaque-release-handle-123456"] = {
        "release": {"guid": "release-guid", "indexerId": 1},
        "expires": time.monotonic() + 60,
    }

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

    calls = []
    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return Response()

    monkeypatch.setattr(httpx, "post", fake_post)
    handle = "opaque-release-handle-123456"
    client.grab(handle)
    assert calls[0][1]["follow_redirects"] is False
    with pytest.raises(ValueError, match="already used"):
        client.grab(handle)
    assert len(calls) == 1


def test_log_redaction_masks_spaced_api_key_labels():
    from remote_access import redact_log_line

    line = redact_log_line("API key=never-log-this")
    assert "never-log-this" not in line
    assert "[REDACTED]" in line


def _start_test_dashboard(monkeypatch, tmp_path, **overrides):
    """Start the real HTTP handler on loopback for deterministic security tests."""
    import socket
    from remote_access import RemoteDashboardServer

    password = "test-only-password-12345"
    salt, verifier = password_verifier(password)
    options = {
        "host": "100.101.20.30",
        "port": 8765,
        "username": "test-user",
        "salt": salt,
        "verifier": verifier,
        "status_provider": lambda: {"engine": "stopped"},
        "action_handler": lambda _action: None,
    }
    options.update(overrides)
    server = RemoteDashboardServer(**options)
    # Binding validation is tested separately; the HTTP handler itself is
    # deliberately exercised over loopback so tests need no Tailscale network.
    server.host = "127.0.0.1"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        server.port = probe.getsockname()[1]
    server.start()
    return server, password


def _dashboard_request(server, method, path, *, body=None, headers=None):
    import http.client
    import json

    connection = http.client.HTTPConnection(server.host, server.port, timeout=3)
    request_headers = {"Host": f"{server.host}:{server.port}"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
        body = json.dumps(body)
    request_headers.update(headers or {})
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    payload = response.read()
    result = (response.status, dict(response.getheaders()), payload)
    connection.close()
    return result


def _login_test_dashboard(server, password):
    import json

    status, headers, body = _dashboard_request(
        server, "POST", "/login",
        body={"username": "test-user", "password": password},
        headers={"Origin": f"http://{server.host}:{server.port}"},
    )
    assert status == 200
    cookie = headers["Set-Cookie"].split(";", 1)[0]
    token = cookie.split("=", 1)[1]
    session = server._sessions[token]
    return cookie, session["csrf"]


def test_http_dashboard_login_csrf_logout_and_session_invalidation():
    from remote_access import RemoteDashboardServer

    server, password = _start_test_dashboard()
    try:
        status, _, _ = _dashboard_request(server, "GET", "/api/status")
        assert status == 401

        cookie, csrf = _login_test_dashboard(server, password)
        status, headers, body = _dashboard_request(
            server, "GET", "/api/status", headers={"Cookie": cookie}
        )
        assert status == 200
        assert headers["Cache-Control"] == "no-store"
        assert headers["X-Content-Type-Options"] == "nosniff"

        status, _, _ = _dashboard_request(
            server, "POST", "/api/action",
            body={"action": "start"},
            headers={
                "Cookie": cookie,
                "Origin": f"http://{server.host}:{server.port}",
            },
        )
        assert status == 403  # authenticated but no CSRF token

        status, _, _ = _dashboard_request(
            server, "POST", "/api/action",
            body={"action": "start"},
            headers={
                "Cookie": cookie,
                "Origin": f"http://{server.host}:{server.port}",
                "X-CSRF-Token": csrf,
            },
        )
        assert status == 202

        status, headers, _ = _dashboard_request(
            server, "POST", "/logout",
            body={},
            headers={
                "Cookie": cookie,
                "Origin": f"http://{server.host}:{server.port}",
                "X-CSRF-Token": csrf,
            },
        )
        assert status == 200
        assert "Max-Age=0" in headers["Set-Cookie"]
        status, _, _ = _dashboard_request(
            server, "GET", "/api/status", headers={"Cookie": cookie}
        )
        assert status == 401
    finally:
        server.stop()


def test_http_dashboard_rejects_bad_host_and_origin():
    server, password = _start_test_dashboard()
    try:
        status, _, _ = _dashboard_request(
            server, "GET", "/", headers={"Host": "attacker.example"}
        )
        assert status == 400

        status, _, _ = _dashboard_request(
            server, "POST", "/login",
            body={"username": "test-user", "password": password},
            headers={"Origin": "http://attacker.example"},
        )
        assert status == 403
        assert not server._sessions
    finally:
        server.stop()


def test_http_dashboard_rejects_oversized_and_transfer_encoded_bodies():
    server, _ = _start_test_dashboard()
    try:
        status, _, _ = _dashboard_request(
            server, "POST", "/login",
            body=None,
            headers={
                "Origin": f"http://{server.host}:{server.port}",
                "Content-Length": "8193",
            },
        )
        assert status == 400

        status, _, _ = _dashboard_request(
            server, "POST", "/login",
            body=None,
            headers={
                "Origin": f"http://{server.host}:{server.port}",
                "Transfer-Encoding": "chunked",
            },
        )
        assert status == 400
    finally:
        server.stop()


def test_http_dashboard_login_rate_limit_is_enforced():
    server, _ = _start_test_dashboard()
    try:
        origin = f"http://{server.host}:{server.port}"
        for _ in range(5):
            status, _, _ = _dashboard_request(
                server, "POST", "/login",
                body={"username": "test-user", "password": "incorrect-password"},
                headers={"Origin": origin},
            )
            assert status == 401
        status, _, _ = _dashboard_request(
            server, "POST", "/login",
            body={"username": "test-user", "password": "incorrect-password"},
            headers={"Origin": origin},
        )
        assert status == 429
    finally:
        server.stop()


def test_http_dashboard_session_expiry_is_enforced():
    import time

    server, password = _start_test_dashboard()
    try:
        cookie, _ = _login_test_dashboard(server, password)
        token = cookie.split("=", 1)[1]
        server._sessions[token]["expires"] = time.time() - 1
        status, _, _ = _dashboard_request(
            server, "GET", "/api/status", headers={"Cookie": cookie}
        )
        assert status == 401
        assert token not in server._sessions
    finally:
        server.stop()
