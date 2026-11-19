# Byparr Manager v0.4.0 Beta

**Release channel:** Public community beta  
**Platform:** Windows 11 x64  
**Status:** Candidate notes — do not publish binary assets until the release checklist in `THIRD_PARTY_NOTICES.md` is complete.

## What's included

- Windows desktop Manager and native installer.
- Dashboard controls for starting, stopping and restarting the Byparr engine.
- API connection and Browser Health diagnostics.
- Prowlarr and qBittorrent connection checks.
- Prowlarr indexer test workflow.
- Windows Credential Manager-backed integration credential storage.
- Expandable logs and timestamped UTF-8 log export.

## Maintainer test report

Build 124 was installed on the maintainer's Windows 11 PC. The maintainer reported:
- Dashboard indicators green.
- Prowlarr connection passed.
- qBittorrent connection passed.
- Prowlarr indexer test through Byparr succeeded.
- A real Prowlarr search returned results.

This is a single-machine smoke test. It does not establish compatibility with every Windows PC, security product, indexer, tracker, Prowlarr version or qBittorrent setup. Community testing is requested.

## Known beta limitations

- This is beta software and may contain bugs.
- Windows 11 x64 is the current target; other Windows versions are not certified.
- Compatibility depends on upstream Byparr, browser runtime, indexers and third-party applications.
- Support is provided by a single maintainer in spare time; response times are not guaranteed.

## How to report issues

Use the GitHub issue forms:
- Bug reports: https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues/new?template=bug_report.yml
- Feature requests: https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues/new?template=feature_request.yml

Include the app version/build, Windows version, steps to reproduce, expected and actual behaviour, and relevant logs after redacting API keys, passwords, cookies, tokens, private URLs and personal data. Do not post security vulnerabilities or secrets publicly; see `SECURITY.md`.

## Attribution and licensing

This is an independent community project, not an official Byparr release and not affiliated with or endorsed by ThePhaseless. The upstream Byparr engine is authored by ThePhaseless. See `LICENSE`, `THIRD_PARTY_NOTICES.md` and `UPSTREAM.lock.json`.

**Release gate:** publish installer/portable binaries only after the exact shipped dependency and browser-runtime inventory, licence texts, redistribution terms and corresponding-source arrangements have been verified.
