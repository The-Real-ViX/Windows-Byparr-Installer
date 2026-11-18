# Byparr Manager v0.4.0 beta testing guide

This candidate is intended for controlled testing on Windows 11 x64. The maintainer has tested the original Build 256 on one Windows PC and an iPad over a private Tailscale network. The additional security-hardening changes require a fresh build and a repeat remote-dashboard smoke test.

## Desktop test pass

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

## Private Tailscale remote-dashboard test pass

Only perform these checks on devices in the intended private tailnet. Do not expose the dashboard port to the public internet.

- [ ] Enable remote access from the desktop Manager using the Windows PC's Tailscale IP.
- [ ] Sign in from an iPad or other tailnet device.
- [ ] Confirm the dashboard refreshes and displays engine/API/browser status.
- [ ] Confirm Start, Stop, Restart and diagnostics controls work.
- [ ] Search each category you use (Movies, TV, Audio/Music, Books, PC, Console).
- [ ] Confirm search results show useful release details without exposing API keys or raw download/magnet URLs.
- [ ] Select a result and confirm the prompt before sending it to Prowlarr's configured download client.
- [ ] Confirm the release appears in qBittorrent and begins downloading.
- [ ] Sign out and confirm the dashboard requires login again.
- [ ] Disable remote access and confirm the remote endpoint stops responding.

## When reporting a problem

Use the Bug report form. Include the app version/build, Windows version, exact steps, expected result, actual result and relevant redacted logs. Say whether the issue happens every time or only sometimes.

**Never attach secrets.** Remove API keys, passwords, cookies, tokens, private tracker URLs, personal names, local file paths and IP addresses before posting logs or screenshots.

## Beta expectations

This project is maintained by one person in spare time. Reports are welcome, but responses and fixes are not guaranteed to be immediate. This is not a public-internet remote-access product and has not undergone an independent penetration test.
