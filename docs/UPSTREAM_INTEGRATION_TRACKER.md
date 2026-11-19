# Upstream Byparr Integration Tracker

Status date: 2026-11-19

## Safety boundaries

- This branch is an isolated integration workspace based on `work/build-389-release-audit`.
- Do not merge this branch into the release-audit branch or `main` until its tests and Windows validation pass.
- Preserve the user-validated Build 388 checkpoint and the Build 130 known-good checkpoint.
- Do not add engine self-updating, Git fetch/pull behavior at application runtime, router port forwarding, or public Internet exposure.
- The Manager UI and existing Arr/qBittorrent/Tailscale integrations remain project-owned and must be preserved.

## Baseline confirmed

- The bundled Byparr source pin is `c81385f59ec978ef81909a273e514ca6d9ace2a9`.
- This is the upstream main revision already used by the Build 400 Windows workflow.
- The corresponding-source artifact contains the pinned source archive, upstream LICENSE, `pyproject.toml`, `uv.lock`, source modules, tests, `UPSTREAM.lock.json`, and source preparation script.
- Build 400 Windows workflow run: https://github.com/The-Real-ViX/Windows-Byparr-Installer/actions/runs/44516319677
- Run result: success. All 37 packaging/test steps completed, including lint, automated tests, Windows Credential Manager verification, runtime SBOM generation, packaged-engine/browser smoke test, installer creation and artifact uploads.
- This is CI success only; it is not yet a user-tested Build 400 release.

## Upstream candidates

### PR #450 — dependency updates (candidate for isolated test)

https://github.com/ThePhaseless/Byparr/pull/450

Changes observed:
- FastAPI `0.162.*` to `0.163.*`
- Playwright `1.64.*` to `1.65.*`
- pytest-asyncio `1.4.*` to `1.5.*`
- lockfile refresh and Docker-only image/action digest changes

Plan:
1. Test the runtime dependencies separately from test-only pytest-asyncio.
2. Verify Playwright 1.65 browser download/cache layout and Firefox startup in the Windows packaged engine.
3. Regenerate engine SBOM and license-screening outputs.
4. Run engine tests, Manager tests, packaged-engine smoke tests and full Windows packaging.
5. Compare installer/portable sizes and browser runtime manifest before considering adoption.

Do not copy Docker-only image digest changes into the Windows build unless a corresponding Windows use is identified.

### PR #435 — optional waitInSeconds (candidate for a focused feature patch)

https://github.com/ThePhaseless/Byparr/pull/435

The proposal adds a non-negative `waitInSeconds` request field and waits after challenge handling to allow dynamic page content to load. It changes the engine request contract.

Plan:
1. Keep the default at zero so existing callers behave identically.
2. Add model validation and endpoint tests for zero, positive, negative and excessive values.
3. Ensure the wait is bounded by the existing request timeout; do not allow it to silently exceed the request's maximum timeout.
4. Add a Manager/API integration test only if the Manager will expose this option.
5. Do not enable a non-zero default.

### PR #441 — HTTP/3 fallback and concurrency redesign (deferred)

https://github.com/ThePhaseless/Byparr/pull/441

This is a substantial browser lifecycle, exception handling, protocol fallback and concurrency refactor. The PR also contains a Windows batch file that performs Git update operations, which is not suitable for this managed installer.

Decision: do not import wholesale. Revisit individual ideas only after isolated review and dedicated tests, without importing runtime self-update behavior.

### PR #448 — Python 3.15 (deferred)

https://github.com/ThePhaseless/Byparr/pull/448

Keep the current Python 3.14 engine runtime until upstream compatibility and all Windows native wheels/browser packaging are proven.

## Build 400 evidence and limits

- Build 400 workflow completed successfully.
- Generated artifacts include installer, portable package, corresponding-source archive, release-candidate evidence bundle and package-size audit.
- Package-size audit reports 3,766 files and 964,096,294 uncompressed bytes.
- The installer artifact is approximately 303.7 MB; portable artifact approximately 426.5 MB.
- The combined release-candidate evidence artifact is approximately 730.1 MB and exceeds the available artifact-download limit in this review environment. Its internal SBOMs, CSV, browser manifest and checksum bundle therefore remain to be inspected before release approval.
- Automated license screening is not legal clearance. Browser runtime, Qt/PySide6, installer tooling and other bundled third-party notices still require human review.
- Build 400 has not been validated by the user on Windows 11. Do not call it release-ready or user-validated.

## Next execution order

1. On this branch, make the PR #450 runtime dependency candidate in a narrow, reversible commit.
2. Run the engine tests and Windows packaging; inspect browser runtime and artifacts.
3. If stable, separately implement and test the optional wait parameter with timeout bounds.
4. Keep PR #441 and Python 3.15 deferred.
5. Compare candidate results against Build 388 behavior before any release-branch promotion.
