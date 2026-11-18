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
    assert "search-form" in DASHBOARD
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
