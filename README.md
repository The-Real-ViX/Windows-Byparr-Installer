# Byparr Manager for Windows

**A community-built Windows 11 desktop manager and installer for the [Byparr](https://github.com/ThePhaseless/Byparr) engine.**

> **Status: public beta preparation — v0.5.0.** This is an independent community project, not an official Byparr release and not affiliated with or endorsed by ThePhaseless. The application has been tested by its maintainer on one Windows 11 computer. Other hardware, Windows configurations and indexer setups still need community testing.

## What it does

Byparr Manager provides a Windows desktop control centre for a locally running Byparr engine:

- Start, stop and restart the Byparr engine.
- Check the local API and browser health.
- View and export timestamped application/engine logs.
- Check Prowlarr and qBittorrent connectivity.
- Run Prowlarr integration diagnostics.
- Store integration credentials using Windows Credential Manager.
- Install or uninstall the Windows application.

The manager is designed to make setup and diagnostics easier. It does not guarantee that every indexer, challenge, browser environment or third-party integration will work.

## Download

Use the **Releases** page for published builds:

https://github.com/The-Real-ViX/Windows-Byparr-Installer/releases

Choose the Windows x64 installer asset for the release. Do not use an Actions build artifact as a permanent download; Actions artifacts expire.

This is beta software. Back up important configuration before installing or updating. The installer is intended for Windows 11 x64. If Windows SmartScreen displays a warning, do not bypass it unless you have independently checked that you downloaded the release from this repository and are comfortable proceeding.

## Remote access over Tailscale

Byparr Manager can optionally bind the Byparr API to this Windows PC's active Tailscale IPv4 address. This keeps the API off the ordinary Wi-Fi/Ethernet interfaces.

1. Install and sign in to Tailscale on the Windows PC that runs Byparr.
2. Install and sign in to Tailscale on the remote device.
3. In Byparr Manager, open **Settings**, enable **Remote access over Tailscale**, refresh the status, and save the setting.
4. Start or restart the Byparr engine. The Manager displays the remote address, for example `http://100.x.y.z:8191`.
5. Configure the Tailscale access policy so only the devices/users you trust can reach TCP port 8191 on this PC.
6. If Prowlarr or another *arr app runs on this same Windows PC, point its Byparr connection at the displayed Tailscale IP while Tailscale-only binding is enabled, rather than using localhost.

**Security:** Tailscale encrypts traffic between tailnet devices, but the Byparr API itself does not provide a Manager username/password. Anyone permitted by your tailnet policy to reach this port may be able to call the API. Do not expose port 8191 through router port forwarding or a public reverse proxy. The feature is opt-in; local-only binding remains the default. The Windows Manager must remain running because it currently supervises the engine process.

If the Tailscale address is not detected, confirm that Tailscale is installed, signed in and connected on the Windows PC, then use **Refresh Tailscale status**. A change to the selected bind address takes effect when the engine next starts or restarts.

## First checks after installation

1. Open Byparr Manager.
2. Confirm the Dashboard reports the API and browser health correctly.
3. Open Integrations and test Prowlarr.
4. Test qBittorrent if you use it.
5. In Prowlarr, run a test on an indexer configured to use Byparr.
6. Try a normal search and check that results return.

Do not post API keys, passwords, cookies, authentication headers, private tracker URLs, or personal information in screenshots or logs.

## Help improve the beta

This project is maintained by one person. Clear reports from people using different Windows PCs and setups are especially valuable.

- **Report a bug:** https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues/new?template=bug_report.yml
- **Suggest an improvement:** https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues/new?template=feature_request.yml
- **Browse existing reports:** https://github.com/The-Real-ViX/Windows-Byparr-Installer/issues

Before opening a report, please check whether someone has already reported the same problem. For a useful bug report, include:

- Byparr Manager version and build number (shown in the app or installer).
- Windows edition and version (run `winver`).
- What you clicked or tried, and what you expected to happen.
- What actually happened and whether you can reproduce it.
- Relevant logs, with secrets and personal details removed.

Please be patient: this is a community beta maintained in spare time, so replies and fixes may not be immediate. Friendly, specific reports are much easier to investigate than “it doesn't work”.

**Security issues:** do not publish vulnerabilities, exposed credentials or sensitive logs in a public issue. See [SECURITY.md](SECURITY.md).

## Privacy and diagnostics

Issue reports are public unless GitHub indicates otherwise. Only attach logs you have reviewed. Redact API keys, passwords, cookies, tokens, private URLs, usernames, local paths and IP addresses if you do not want them public. Never send credentials to the maintainer.

## Project scope and limitations

- Windows 11 x64 is the current target.
- The underlying Byparr engine is an upstream component pinned in `UPSTREAM.lock.json`.
- Prowlarr and qBittorrent diagnostics are included; compatibility can still vary with their versions and individual indexers.
- This is beta software and may contain defects. Keep backups and use it at your own discretion.
- No response time, support level or compatibility guarantee is promised.

## Source, licence and attribution

This repository contains the manager, installer, build scripts and the pinned upstream revision information. The Byparr engine is authored by **ThePhaseless** and is licensed under **GNU GPL-3.0**. See [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and [UPSTREAM.lock.json](UPSTREAM.lock.json).

The manager/installer work is maintained by **RedHeX**, with project development assistance credited to **The TinMan**. These credits do not imply ownership of or endorsement by the upstream Byparr author.

## Contributions

Constructive bug reports, testing feedback, documentation improvements and pull requests are welcome. Please keep changes focused and preserve upstream notices and licence obligations.

---

Provided without warranty. Byparr and third-party names and marks belong to their respective owners.
