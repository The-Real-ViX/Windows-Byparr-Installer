# Windows Byparr Installer

**A Windows 11 installer and management application for Byparr**  
Maintained by **RedHeX** · Project credits: **RedHeX & The TinMan**

> This is an independent community project. It is not affiliated with, endorsed by, or an official release of the original Byparr project or its author.

## What this project aims to provide

A beginner-friendly Windows 11 installation and control centre for the original [Byparr](https://github.com/ThePhaseless/Byparr) engine, with the engine kept as a separately identifiable upstream component.

Planned capabilities:

- Native Windows installer and uninstaller — no Docker requirement.
- Guided setup of required runtimes and browser components.
- A modern Windows 11 management interface for service status, start/stop/restart, configuration, logs and diagnostics.
- Background service installation and optional start-at-login/boot.
- Prowlarr connection checks and guided configuration, with Jackett support.
- A controlled upstream update workflow that checks new Byparr releases/commits, tests compatibility, and allows rollback rather than blindly replacing a working installation.
- Clear third-party notices, source availability and licence information.

## Project status

**Early development / repository scaffold.** Features listed above are goals, not claims that an installer or Windows service is already complete. The manager interface has an early Mac preview for development, but the final target is Windows 11. The original Byparr browser engine must be tested on Windows before a Windows release can be called working.

## Relationship to Prowlarr, Jackett and Jellyfin

Byparr is intended to act as a browser-challenge solving service for compatible indexer workflows. This project will focus on helping users connect and verify Prowlarr (priority) and Jackett.

Jellyfin remains responsible for managing and streaming the user's media library. This project does not replace Jellyfin or directly manage media files; it is intended to fit alongside a setup where Prowlarr and related download tools feed a Jellyfin library.

## Upstream project and attribution

The underlying Byparr engine is created and maintained by **ThePhaseless**:

- Original project: https://github.com/ThePhaseless/Byparr
- The upstream repository's GNU General Public License, version 3, is included in this repository as `LICENSE`.
- Original copyright and licence notices in upstream files must be preserved.
- Windows-specific changes and this management/installer layer will be clearly identified as modifications/additions by this project.
- RedHeX and The TinMan credits apply only to contributions made in this repository; they do not replace or claim ownership of upstream work.

## Licensing

The upstream Byparr project provides its code under **GNU GPL-3.0**. This repository is being developed with the intention of distributing the combined project in a GPL-3.0-compliant way. The exact licensing and packaging of every bundled dependency will be documented before binary releases.

If binaries are distributed, the corresponding source and required notices will be made available in accordance with the applicable licences. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Development principles

1. Preserve upstream attribution and notices.
2. Keep upstream engine code identifiable and avoid unnecessary changes to it.
3. Review and test upstream updates before adopting them.
4. Never claim Windows compatibility until it has been tested on Windows 11.
5. Make destructive actions explicit and provide clear diagnostics and rollback paths.

## Contributions and issue reports

This project is under active development. Bug reports, compatibility notes and constructive contributions are welcome. Please include Windows version, application version, relevant logs (with API keys and personal data removed), and steps to reproduce.

## Credits

- **ThePhaseless** — original Byparr project and engine.
- **RedHeX** — Windows installer/manager project.
- **The TinMan** — project development assistance and documentation.

---
This project is provided without warranty. Byparr and the names/logos of other third-party projects remain the property of their respective authors.
