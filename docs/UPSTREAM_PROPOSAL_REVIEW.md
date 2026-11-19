# Upstream proposal review — 17 November 2026

This file tracks selected proposals in the upstream [ThePhaseless/Byparr](https://github.com/ThePhaseless/Byparr) repository. These are upstream pull requests, not merged upstream releases. The pinned engine remains the exact upstream `main` revision recorded in `UPSTREAM.lock.json`; none of the open proposals below is silently represented as part of that source.

## Decisions

| Upstream proposal | Decision for Byparr Manager | Reason / next gate |
| --- | --- | --- |
| [#425 — IPv6 troubleshooting](https://github.com/ThePhaseless/Byparr/pull/425) | **Adopt the troubleshooting guidance in our documentation.** | Useful when Byparr and Prowlarr/Jackett run in separate containers or networks and use different public IP address families. This is diagnostic guidance, not a reason to disable IPv6 globally on Windows. |
| [#435 — FlareSolverr `waitInSeconds`](https://github.com/ThePhaseless/Byparr/pull/435) | **Candidate for a later engine update.** | Adds an optional request field to the upstream API. Wait until upstream merges it or we can maintain a clearly isolated, tested patch; then add API-contract tests and verify compatibility with real callers. |
| [#450 — dependency pin updates (Playwright 1.65.x and pytest-asyncio 1.5.x)](https://github.com/ThePhaseless/Byparr/pull/450) | **Defer until merged and tested upstream.** | Playwright changes affect the browser runtime bundled into the Windows application. Update the lock only after Windows browser startup, health, and Prowlarr regression tests pass. |
| [#448 — Python 3.15 requirement](https://github.com/ThePhaseless/Byparr/pull/448) | **Do not adopt while the proposal is open.** | The current pinned engine is built with Python 3.14. The Manager itself has a separate build runtime. A Python major/minor runtime change needs a fresh Windows packaging and browser smoke-test cycle. |
| [#441 — HTTP/3 fallback and concurrency advisor](https://github.com/ThePhaseless/Byparr/pull/441) | **Do not import this PR wholesale. Revisit selectively.** | It changes browser lifecycle, concurrency control and HTTP/3 behaviour together, so it needs focused design review and load/browser tests. Its patch also contains a Windows batch file that fetches and pulls Git updates automatically; that behaviour is not suitable for our installer and must not be adopted. No silent engine self-updates. |
| [#445 — README cache note](https://github.com/ThePhaseless/Byparr/pull/445) | **No code change required.** | Keep the upstream cache/runtime behaviour in mind when reviewing future packaging changes; do not change the Windows Manager based on a documentation-only proposal. |

## Update policy

1. Keep the known-good pinned engine unchanged while the current beta is being stabilized.
2. Prefer changes after they are merged into upstream `main` or included in an upstream release.
3. For any candidate engine change, build it on a separate development branch and retain the previous pinned engine for rollback.
4. Run the Windows engine package smoke test, API checks, browser health check, Prowlarr indexer test and a real Prowlarr search before promotion.
5. Update `UPSTREAM.lock.json`, this review, the dependency inventory and release notes together. Never claim an open upstream PR is part of the upstream release.

Last reviewed: 17 November 2026.
