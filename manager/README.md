# Byparr Manager — Windows

Byparr Manager is an independent community-built Windows desktop control centre for the upstream [Byparr](https://github.com/ThePhaseless/Byparr) engine.

**Version:** 0.4.0 Beta  
**Platform:** Windows 11 x64

## Main features

- Start, stop and restart the local Byparr engine.
- Check API connectivity and Browser Health.
- View and export timestamped application and engine logs.
- Check Prowlarr and qBittorrent connectivity.
- Run Prowlarr integration diagnostics.
- Store integration credentials using Windows Credential Manager.
- Optional password-protected remote dashboard over your private Tailscale network.

## First run

1. Launch Byparr Manager.
2. On the Dashboard, check the API and Browser Health indicators.
3. Open Integrations and test Prowlarr and qBittorrent if configured.
4. In Prowlarr, test an indexer configured to use Byparr, then try a search.
5. If something fails, open Logs and export the relevant diagnostic output.

The Manager launches the engine locally by default. Keep the API bound to localhost unless you intentionally need trusted network access and understand the exposure.


## Optional remote dashboard (Tailscale)

Remote access is **off by default**. To use it, open **Settings → Tailscale remote dashboard** on the Windows PC:

1. Enter that PC's Tailscale IP address (normally in the `100.x.x.x` range).
2. Leave the suggested port `8765`, unless another app already uses it.
3. Choose a dedicated dashboard username and a strong password of at least 14 characters.
4. Select **Enable remote access**. The dashboard is available only while Byparr Manager remains open and remote access is enabled.
5. On another device connected to the same tailnet, browse to `http://TAILSCALE-IP:8765` and sign in.

The remote service binds to the specified Tailscale address only. It does not bind to every network interface, change the Byparr engine's localhost binding, configure router port forwarding, or use Tailscale Funnel. Tailscale encrypts traffic between tailnet devices; keep your tailnet access controls restricted to devices and people you trust. The dashboard also has its own login, salted password verifier, expiring sessions, CSRF checks, and login throttling. It exposes only the Manager dashboard actions, not a general Windows command prompt or file browser.

The password is not saved in plain text. Only a salted PBKDF2 verifier is stored in local application settings. Remote access stops when the Manager closes; enable it again manually when needed. Use a unique password, not your Windows, Prowlarr, or qBittorrent password.

This initial remote dashboard provides engine status and start/stop/restart controls plus recent redacted logs. It is an early feature and should be tested on your own trusted tailnet before relying on it. The Byparr engine API remains bound to localhost.

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
