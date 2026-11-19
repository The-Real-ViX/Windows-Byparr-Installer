# Byparr Manager v0.4.0 Beta

**Release channel:** Private beta candidate  
**Platform:** Windows 11 x64  
**Status:** Candidate notes. This build is intended for controlled testing on the maintainer's private Tailscale network. It is not approved for public binary distribution until the release checklist in `THIRD_PARTY_NOTICES.md` is complete.

## What's included

- Windows desktop Manager and native installer.
- Dashboard controls for starting, stopping and restarting the Byparr engine.
- API connection and Browser Health diagnostics.
- Prowlarr and qBittorrent connection checks.
- Prowlarr indexer diagnostics.
- Windows Credential Manager-backed integration credential storage.
- Expandable logs and timestamped UTF-8 log export.
- Optional remote dashboard bound to a configured Tailscale IP.
- Dedicated remote dashboard login, CSRF protection, login throttling, session expiry, request-origin checks and redacted audit logs.
- iPad-friendly Prowlarr search with categories: All, Movies, TV Shows, Audio/Music, Books, PC and Console.
- Release selection and submission to Prowlarr's configured download client without exposing API keys, magnet links or download URLs to the browser.

## Maintainer test report

The maintainer reported that Build 256 completed a real end-to-end test on one Windows 11 PC and an iPad on the private tailnet:
- Remote Tailscale login succeeded.
- Byparr engine started and API readiness passed.
- Browser Health reported healthy.
- Prowlarr and qBittorrent diagnostics passed.
- An Audio/Music search returned 50 results.
- Byparr cleared an indexer challenge.
- A selected release was accepted by Prowlarr and confirmed by the maintainer as downloading in qBittorrent.

The additional security-hardening changes after Build 256 require a fresh package build and a repeat iPad login/dashboard smoke test. This is a single-machine test, not a broad compatibility assessment or independent penetration test.

## Remote access safety

Remote access is opt-in and binds only to the configured Tailscale address. The dashboard uses HTTP over Tailscale; Tailscale encrypts traffic between tailnet devices. Do not expose the port through router forwarding, Tailscale Funnel or a public reverse proxy. See `docs/REMOTE_DASHBOARD_SECURITY_REVIEW.md`.

## Known beta limitations

- This is beta software and may contain bugs.
- Windows 11 x64 is the current target; other Windows versions are not certified.
- Compatibility depends on upstream Byparr, browser runtime, indexers and third-party applications.
- The remote dashboard is designed for a private tailnet, not the public internet.
- No independent security penetration test has been performed.
- Support is provided by a single maintainer in spare time; response times are not guaranteed.

## How to report issues

Use the GitHub issue forms:
- Bug reports: https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues/new?template=bug_report.yml
- Feature requests: https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues/new?template=feature_request.yml

Include the app version/build, Windows version, steps to reproduce, expected and actual behaviour, and relevant logs after redacting API keys, passwords, cookies, tokens, private URLs and personal data. Do not post security vulnerabilities or secrets publicly; see `SECURITY.md`.

## Attribution and licensing

This is an independent community project, not an official Byparr release and not affiliated with or endorsed by ThePhaseless. The upstream Byparr engine is authored by ThePhaseless. See `LICENSE`, `THIRD_PARTY_NOTICES.md` and `UPSTREAM.lock.json`.

**Public binary release gate:** publish installer/portable binaries only after the exact shipped dependency and browser-runtime inventory, licence texts, redistribution terms and corresponding-source arrangements have been verified.
