import subprocess

from tailscale import get_tailscale_ipv4


def test_returns_tailscale_ipv4_from_cli(monkeypatch):
    monkeypatch.setattr("tailscale.find_tailscale_cli", lambda: "tailscale")
    monkeypatch.setattr(
        "tailscale.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="100.101.102.103\n", stderr=""
        ),
    )

    assert get_tailscale_ipv4() == "100.101.102.103"


def test_ignores_non_tailscale_ipv4(monkeypatch):
    monkeypatch.setattr("tailscale.find_tailscale_cli", lambda: "tailscale")
    monkeypatch.setattr(
        "tailscale.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="192.168.1.20\n", stderr=""
        ),
    )

    assert get_tailscale_ipv4() is None


def test_returns_none_when_cli_is_missing(monkeypatch):
    monkeypatch.setattr("tailscale.find_tailscale_cli", lambda: None)

    assert get_tailscale_ipv4() is None


def test_returns_none_when_cli_fails(monkeypatch):
    monkeypatch.setattr("tailscale.find_tailscale_cli", lambda: "tailscale")
    monkeypatch.setattr(
        "tailscale.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="", stderr="not connected"
        ),
    )

    assert get_tailscale_ipv4() is None
