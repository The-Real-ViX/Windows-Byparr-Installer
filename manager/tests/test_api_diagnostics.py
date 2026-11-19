from api_diagnostics import format_api_diagnostic


def test_api_diagnostic_includes_status_duration_and_safe_detail():
    line = format_api_diagnostic("Radarr", True, 200, 42, "Connected (version 6.0)")
    assert "API CHECK | Radarr | PASS | HTTP 200 | 42 ms" in line
    assert "Connected (version 6.0)" in line
    assert line.startswith("[")


def test_api_diagnostic_redacts_secret_values_and_removes_newlines():
    line = format_api_diagnostic(
        "Prowlarr", False, 401, 12, "API key=super-secret\npassword: also-secret"
    )
    assert "super-secret" not in line
    assert "also-secret" not in line
    assert "[REDACTED]" in line
    assert "\n" not in line


def test_api_diagnostic_handles_missing_http_status():
    line = format_api_diagnostic("Byparr", False, None, 3000, "Could not connect")
    assert "HTTP n/a | 3000 ms" in line
