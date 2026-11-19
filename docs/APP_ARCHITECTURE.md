# Application architecture

This document defines the intended boundaries before the manager and installer are implemented. It is a design contract, not a claim that these components already exist.

## Design principles

- Keep the upstream Byparr application in its own vendor directory and preserve its original files and notices.
- Keep RedHeX manager code separate from upstream code.
- Do not patch upstream behaviour silently. Put Windows-specific orchestration and any compatibility layer in this project.
- Treat every displayed status as measured state. Never show a green "working" indicator based only on a process existing.
- Make setup, repair, update and uninstall repeatable and safe. Preserve configuration and logs unless the user explicitly chooses to remove them.
- Do not start a browser challenge merely to decide whether the local API process is alive.

## Planned repository layout

```text
Windows-Byparr-Installer/
  manager/                 # RedHeX desktop control centre
  service/                 # Windows process/service lifecycle and probes
  integrations/
    prowlarr/              # Explicit FlareSolverr-compatibility adapter, if required
    jackett/               # Separately validated Jackett integration
  scripts/                 # Setup, source preparation and project checks
  vendor/Byparr/           # Unmodified pinned upstream source (prepared locally)
  installer/               # Native Windows installer assets and scripts
  docs/                    # Design, compatibility, test and release notes
  UPSTREAM.lock.json       # Exact upstream source revision
```

Folders may be introduced incrementally as their first real implementation lands; empty placeholder packages are intentionally avoided.

## Runtime responsibilities

### Manager

The desktop manager is the user-facing control centre. It should own presentation, user settings, configuration validation, log viewing and diagnostic summaries. It should call a small service-management interface rather than embedding Windows service commands throughout UI event handlers.

### Runtime supervisor

The supervisor is responsible for starting and stopping the Byparr process, tracking its PID/exit code, collecting logs, applying configured bind address and port, and shutting down cleanly. It must not report "browser ready" just because the process started.

### Health probes

Expose three distinct results:

1. **Process** — the managed process/service exists and is in the expected state.
2. **API** — a bounded-time HTTP request to the local OpenAPI endpoint succeeds.
3. **Browser operation** — a deliberate, user-triggered or scheduled test confirms the browser runtime can perform its intended work.

A failed browser operation should not automatically be described as an API outage. Record the stage and useful error details without exposing secrets.

### Tailscale remote access

Remote access is opt-in. When enabled, the Manager discovers the active Tailscale IPv4 address using the local Tailscale CLI and configures the engine to bind only to that address. It must never silently fall back to a wildcard bind such as `0.0.0.0`. If Tailscale is unavailable, remote-mode engine startup is blocked with a clear explanation. Local-only loopback binding remains the default.

Tailscale provides the encrypted network path and tailnet access policy; it does not add application-level authentication to the Byparr API. Documentation must make this distinction explicit. Do not create router port-forwarding rules or public reverse-proxy exposure as part of this feature. The Manager currently supervises the engine process, so the Manager must remain open while remote access is needed.

### Integration adapters

Prowlarr and Jackett adapters must be based on the current supported contracts of those applications. If Prowlarr expects the FlareSolverr protocol, the project must provide a separately tested translation layer where the pinned Byparr API differs. The native Byparr endpoint must not be presented as FlareSolverr-compatible without evidence.

## Configuration and secrets

- Keep bind address and port explicit; default upstream values are not silently assumed to be safe for every installation.
- Prefer loopback binding for a local-only deployment unless the user explicitly configures LAN access.
- Never log API keys, bearer tokens, passwords, cookies or full secret-bearing URLs.
- Store credentials using an appropriate Windows-protected mechanism when credential storage is implemented.
- Validate ports, paths and URLs before applying configuration.

## Install, update and uninstall behaviour

- Install must detect prerequisites and explain missing components before changing the machine.
- Repair must preserve user configuration and diagnostic logs.
- Update must stage the new engine, validate it, then promote it; retain a rollback copy of the last known-good engine.
- Uninstall must stop the managed service and remove application binaries. Preserve user configuration and logs by default, with a clearly separate opt-in cleanup choice.
- The upstream source and licence notices must remain available for every distributed release in accordance with the applicable licence.

## Verification gates

A feature is not release-ready until it has:
- automated checks for its non-platform-specific logic;
- Windows 11 validation on a real target machine or equivalent supported CI environment;
- clear failure handling and useful diagnostics;
- documentation of what was and was not tested.

The manager UI may be previewed on macOS during development, but that does not validate the Windows browser engine or service lifecycle.
