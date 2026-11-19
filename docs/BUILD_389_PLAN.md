# Build 389 preparation plan

**Baseline:** Build 388, commit fd994b6556357a48cba618e7990c05ed39accda9  
**Validated environment:** One Windows 11 PC and one iPad on the owner's private Tailscale network  
**Working branch:** work/build-389-release-audit  
**Status:** Planning and audit only; no Build 389 installer is approved or available yet.

## Baseline preservation

- Keep checkpoint/build-130-known-good unchanged.
- Keep checkpoint/build-388-user-validated at the exact Build 388 commit.
- Do not merge PR #2 or publish a public binary release as part of this work.
- Preserve the Build 365 installer as the user's fallback.

## Build 388 validation recorded

The Build 388 desktop, engine, four integrations, browser health, qBittorrent handoff, in-app logs, no-automatic-Desktop-log behaviour, and repeat iPad Tailscale search/grab workflow were reported successful on 2026-11-19. The detailed test record is in BETA_TESTING.md. This is a single-environment user test, not an independent security assessment.

## Audit findings

### Security posture

The static review found useful existing controls: opt-in binding to a Tailscale address, localhost-only engine API, dedicated dashboard authentication, salted PBKDF2-HMAC-SHA256 password verification, per-IP login throttling, bounded request bodies and concurrent connections, Host/Origin validation, CSRF tokens, expiring client-bound sessions, CSP nonce, redacted audit logs, and opaque single-use release-grab handles.

Operating limits remain material:
- The dashboard is HTTP, not application-level HTTPS; rely on Tailscale's encrypted tailnet transport and ACLs.
- Do not use router port forwarding, Tailscale Funnel, public reverse proxies, or expose the dashboard to the public internet.
- Login throttling is in-memory and resets when the Manager restarts.
- The Python standard-library threaded HTTP server is deliberately not an internet-facing web server.
- No independent penetration test or formal security certification has been completed.

### Packaging and licensing

THIRD_PARTY_NOTICES.md explicitly says the shipped-component inventory is incomplete. The final Windows package includes the Manager's Python dependencies and native Qt components, the pinned Byparr engine dependency tree, Invisible Playwright/Playwright components, and a fetched browser runtime. Exact versions, copyright holders, licence identifiers/texts, redistribution terms, and corresponding-source arrangements still need to be derived from the actual package.

A public binary release remains blocked until:
- An SBOM is generated from the exact packaged Windows build.
- Shipped packages, native libraries, Qt/PySide6 components and browser runtime are inventoried and their licence terms checked.
- Required licence texts and notices are included.
- GPL-covered corresponding source and project modifications are made available as required.
- Final installer/portable checksums and source/build identities are recorded.

### Test coverage gaps to close

Existing unit tests cover important validation, redaction, search mapping and single-use grab-handle behaviour. Before another candidate, add or strengthen regression tests for the live HTTP request flow where practical: login, CSRF rejection, session expiry/logout, Host/Origin rejection, malformed/oversized bodies, rate limiting, and server shutdown/concurrency. Keep tests deterministic and avoid requiring a live Tailscale network.

## Proposed Build 389 scope

Build 389 should be a maintenance and release-engineering candidate, not a feature/UI redesign.

1. Add deterministic remote-dashboard HTTP regression tests for the security boundaries listed above.
2. Generate an SBOM and exact dependency inventory from the same Windows build that produces the installer and portable artifact.
3. Produce a licence audit report distinguishing shipped runtime components from build-only tooling; include the required licence texts/notices and verify the pinned Byparr source/corresponding-source package.
4. Keep package-size reporting and SHA-256 checksums alongside the candidate artifacts.
5. Re-run all CI checks, Windows packaging/engine smoke tests, then repeat the core Build 388 user test before treating Build 389 as validated.

Do not add unrelated UI features, upgrade the pinned Byparr engine, change the remote-access trust model, or weaken any existing security control in this build.

## Release decision

- **Private controlled beta:** may be considered only after all relevant CI jobs and Windows packaging checks pass and the exact candidate artifacts are inspected.
- **Public binary release:** not approved until the packaging/licensing gate above is complete.
- **Merge:** keep PR #2 open and in draft until the separate review and release gates are satisfied.
