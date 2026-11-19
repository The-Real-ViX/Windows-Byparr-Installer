# Byparr Manager — Windows

Byparr Manager is an independent community-built Windows desktop control centre for the upstream [Byparr](https://github.com/ThePhaseless/Byparr) engine.

**Version:** 0.5.0 Beta  
**Platform:** Windows 11 x64

## Main features

- Start, stop and restart the local Byparr engine.
- Check API connectivity and Browser Health.
- View and export timestamped application and engine logs.
- Check Prowlarr and qBittorrent connectivity.
- Run Prowlarr integration diagnostics.
- Store integration credentials using Windows Credential Manager.

## First run

1. Launch Byparr Manager.
2. On the Dashboard, check the API and Browser Health indicators.
3. Open Integrations and test Prowlarr and qBittorrent if configured.
4. In Prowlarr, test an indexer configured to use Byparr, then try a search.
5. If something fails, open Logs and export the relevant diagnostic output.

The Manager launches the engine locally by default. Keep the API bound to localhost unless you intentionally need trusted network access and understand the exposure.

## Reporting problems

This is beta software maintained by one person in spare time. Reports and testing feedback are welcome, but response times are not guaranteed.

- Bug reports: https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues/new?template=bug_report.yml
- Feature requests: https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues/new?template=feature_request.yml
- Testing guide: https://github.com/The-Real-ViX/Windows-Byparr-Installer/blob/main/docs/BETA_TESTING.md

Include the Manager version/build, Windows version, steps to reproduce, and expected versus actual behaviour.

**Before sharing logs or screenshots, remove API keys, passwords, cookies, tokens, private tracker URLs, usernames, local paths, IP addresses and other personal information. Never post secrets or suspected security vulnerabilities in a public issue.** See the repository's SECURITY.md.

## Project status and attribution

This is a community beta, not a finished or officially supported Byparr release. The upstream Byparr engine is authored by ThePhaseless. This Manager is an independent project and is not affiliated with or endorsed by the upstream author.

See the repository's LICENSE and THIRD_PARTY_NOTICES.md for licence and attribution information. Binary distribution is subject to completion of the release dependency and licence inventory.
