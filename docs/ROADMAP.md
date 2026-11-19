# Development roadmap

This roadmap describes intended work; unchecked items are not implemented yet.

## Phase 1 — foundation
- [x] Create public project repository.
- [x] Document project scope, upstream attribution and licence baseline.
- [x] Establish initial pinned upstream source metadata and safe source preparation script.\n- [x] Add Windows PowerShell integrity checks and GitHub Actions workflow.\n- [x] Define manager, runtime-supervisor, health-probe and integration boundaries in an architecture note.
- [ ] Establish reproducible development environment.
- [ ] Bring upstream Byparr source into a clearly separated vendor/upstream area.
- [ ] Record upstream commit/tag and dependency versions.

## Phase 2 — Windows engine runtime
- [ ] Confirm upstream engine support and browser requirements on Windows 11.
- [ ] Build a repeatable Windows setup script.
- [ ] Add health/API checks that distinguish API availability from browser challenge success.
- [ ] Add service lifecycle management, logs and safe shutdown.

## Phase 3 — Manager application
- [x] Add opt-in Tailscale-only API binding and connection status to the Manager.
- [ ] Polish Windows 11 dark control-centre UI and RedHeX branding.
- [ ] Dashboard, service controls, configuration, logs and diagnostics.
- [ ] About/Credits and licence notices.
- [ ] Make each control report real state; no mock success states.

## Phase 4 — integrations
- [ ] Prowlarr connection and API checks (priority).
- [ ] Guided FlareSolverr-compatible proxy configuration where supported by current Prowlarr.
- [ ] End-to-end indexer challenge test.
- [ ] Jackett compatibility checks and guidance.
- [ ] Document how the service fits into a Jellyfin media setup.

## Phase 5 — installer and release
- [ ] Native Windows 11 installer and uninstaller.
- [ ] Dependency/browser setup and repair flow.
- [ ] Service startup configuration and clean removal.
- [ ] Windows 11 test matrix and signed/verified release process.
- [ ] Publish source and third-party notices alongside every binary release.

## Upstream update policy

Upstream changes should be detected, reviewed and tested in an isolated update branch/build. Promote an update only after API, browser, service and Prowlarr regression checks pass. Keep the previous known-good version available for rollback. Never silently overwrite a working engine with an untested upstream change.
