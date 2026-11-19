"""Discover the active Tailscale IPv4 address without changing network settings."""

from __future__ import annotations

import ipaddress
import os
import shutil
import subprocess
from pathlib import Path

TAILSCALE_IPV4_RANGE = ipaddress.ip_network("100.64.0.0/10")


def find_tailscale_cli() -> str | None:
    """Find the Tailscale CLI on PATH or in its standard Windows install folder."""
    on_path = shutil.which("tailscale")
    if on_path:
        return on_path

    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    candidates = (
        program_files / "Tailscale" / "tailscale.exe",
        program_files / "Tailscale IPN" / "tailscale.exe",
    )
    return next((str(path) for path in candidates if path.is_file()), None)


def get_tailscale_ipv4() -> str | None:
    """Return the machine's active Tailscale IPv4 address, or None if unavailable."""
    cli = find_tailscale_cli()
    if not cli:
        return None

    try:
        result = subprocess.run(
            [cli, "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        try:
            address = ipaddress.ip_address(line.strip())
        except ValueError:
            continue
        if isinstance(address, ipaddress.IPv4Address) and address in TAILSCALE_IPV4_RANGE:
            return str(address)
    return None
