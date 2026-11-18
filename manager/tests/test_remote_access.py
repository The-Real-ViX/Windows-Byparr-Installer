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
