# Byparr Manager

A Windows-first desktop manager for the pinned upstream Byparr engine.

## Current development status

The Manager provides a Dashboard, Integrations, Settings, and Logs pages. The Dashboard now has a Windows engine process controller with Start, Stop, and Restart actions, process output logging, and API readiness monitoring.

The Windows CI build is being extended to package the pinned Byparr source as a standalone engine executable and include its verified Invisible Playwright browser runtime. The intention is that the final Windows installation will not require a separately installed Python, Docker, Brave, or Chrome.

**This is still a development build, not yet a finished installer.** The bundled engine and browser must pass the packaged Windows smoke test before a test build is offered for installation on the target laptop. The final installer and update/uninstall workflow are still to come.

## Runtime layout

The packaged Windows application is intended to contain:

- `ByparrManager.exe`: the desktop management interface.
- `engine/ByparrEngine/`: the separately packaged Byparr API engine.
- `engine/browser-engine/`: the verified, read-only patched browser runtime bundled with the application.
- Per-user `browser-cache/`: writable browser state kept in the user's local application data folder.

The Manager launches the engine locally on `127.0.0.1` and the configured API port (default `8191`). It monitors `/openapi.json` for readiness and captures engine output in its Logs page. It attempts a graceful stop and uses a forced stop only as a fallback.

## Integrations and settings

Prowlarr and Jackett API keys are stored through the operating-system credential vault using Python Keyring. The Manager does not write those keys to its settings file or fall back to plaintext if a supported vault is unavailable.

The API host and port are stored locally using Qt settings. Keep the API bound to localhost unless you have deliberately configured a trusted network.

## Development

The desktop Manager is built with PySide6. The engine is pinned in the repository's `UPSTREAM.lock.json` and uses the upstream project's locked Python 3.14 dependencies.

The Windows GitHub Actions workflow builds and tests the Windows application. The Mac can be used as an optional development workstation, but it is not a release target for the current project phase.

## Licensing

Byparr is distributed under GPL-3.0. See the repository's `LICENSE` and `THIRD_PARTY_NOTICES.md` for licensing and attribution details.
