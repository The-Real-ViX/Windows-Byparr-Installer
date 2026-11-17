# Community beta testing guide

Byparr Manager v0.4.0 is a beta. The maintainer has tested the current Windows build on one Windows 11 PC, including the dashboard checks, Prowlarr connection, qBittorrent connection, an indexer test through Byparr, and a real Prowlarr search. Community testing is needed across other PCs and configurations.

## Suggested test pass

- [ ] Install on a supported Windows 11 x64 PC.
- [ ] Launch the Manager and check Dashboard/API status.
- [ ] Check Browser Health.
- [ ] Start, stop and restart the Byparr engine.
- [ ] Open the Logs page and export a log.
- [ ] Test Prowlarr connectivity.
- [ ] Test qBittorrent connectivity if configured.
- [ ] Run an indexer test in Prowlarr using Byparr.
- [ ] Run a normal search and confirm whether results return.
- [ ] Close and reopen the Manager; check that settings persist.
- [ ] If practical, test uninstall behaviour and confirm personal settings are retained unless you explicitly choose full cleanup.

## When reporting a problem

Use the Bug report form. Include the app version/build, Windows version, exact steps, expected result, actual result and relevant redacted logs. Say whether the issue happens every time or only sometimes.

**Never attach secrets.** Remove API keys, passwords, cookies, tokens, private tracker URLs, personal names, local file paths and IP addresses before posting logs or screenshots.

## Beta expectations

This project is maintained by one person in spare time. Reports are welcome, but responses and fixes are not guaranteed to be immediate. Please be respectful and patient, and check existing reports before opening a duplicate.
