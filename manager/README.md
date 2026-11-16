# Byparr Manager

The PySide6 desktop interface for the Windows Byparr Installer project.

## Current status

This is the recovered v0.4 interface preview. It provides a Dashboard, Integrations, Settings, and Logs pages, plus a local API connectivity check.

The manager interface is being developed on macOS. The intended production target is Windows 11. The Byparr engine, Windows service lifecycle, installer, and Prowlarr/Jackett integration workflows are **not yet implemented** by this interface. The dashboard's disabled service buttons are deliberate placeholders.

The API check targets `http://127.0.0.1:8191/openapi.json`. It only reports whether that endpoint responds; it does not prove browser challenge solving works.

## Requirements

- Python 3.12 or newer
- `uv` (recommended) or `pip`
- macOS can be used for interface development and preview.
- Windows 11 is required to validate the final service and installer behaviour.

## Run on macOS

From the repository root:

```bash
cd manager
uv sync
uv run python main.py
```

If you prefer pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python main.py
```

## Development checks

From the `manager` directory:

```bash
uv sync --extra dev
uv run ruff check .
uv run python -m compileall -q .
```

## Planned next steps

1. Separate UI pages and shared widgets into maintainable modules.
2. Move API checks into a worker thread so the interface never freezes.
3. Add persistent, validated settings and safe secret storage.
4. Add structured application logging and diagnostics.
5. Implement a Windows runtime supervisor and service lifecycle behind a platform-specific boundary.
6. Add Prowlarr and Jackett configuration and connection tests.
7. Package and test the application on Windows 11.
