# Upstream compatibility notes

This document records facts checked against the upstream Byparr source during initial project setup. Re-check them whenever an upstream revision is imported.

## Source of truth

- Repository: https://github.com/ThePhaseless/Byparr
- Licence file: upstream `LICENSE` (GNU GPL version 3)
- Python requirement in the checked `pyproject.toml`: Python 3.14.x
- Checked dependency declarations include FastAPI, `invisible-playwright`, Playwright and Pydantic.
- Default bind address: `0.0.0.0`
- Default port: `8191`

Do not copy these values into permanent installer assumptions without checking the exact upstream commit being packaged.

## HTTP surface observed in upstream source

The checked source currently defines:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Redirects to the API documentation at `/docs`. |
| GET | `/health` | Performs a browser-backed request to Google and reports health only if that operation succeeds. |
| POST | `/v1` | Main browser-navigation/challenge-solving endpoint; accepts a Byparr `LinkRequest` and returns a `LinkResponse`. |
| POST | `/load` | Open WebUI URL-loading endpoint; can require a bearer token when `OWUI_API_KEY` is configured. |
| GET | `/docs` | FastAPI interactive API documentation. |
| GET | `/openapi.json` | OpenAPI schema, useful for checking that the HTTP API is reachable without launching a browser challenge. |

**Important health-check distinction:** `/health` is not a lightweight process check. It launches browser work and can fail because the browser runtime or target site is unavailable. The manager should report separate states for (1) process/service running, (2) HTTP API reachable, and (3) browser challenge operation verified. A successful `/docs` or `/openapi.json` request proves API reachability, not that challenge solving works.

## Prowlarr and Jackett integration caution

Do not assume that Byparr's `POST /v1` contract is identical to the FlareSolverr API contract simply because Prowlarr supports FlareSolverr-compatible integrations. The checked Byparr endpoint uses its own `LinkRequest`/`LinkResponse` models. Before implementing a Prowlarr wizard, compare the exact request/response schemas expected by the current Prowlarr release with the pinned Byparr release.

If the contracts differ, implement and test a small, explicit compatibility adapter rather than mislabelling the native Byparr API as FlareSolverr. Jackett support must be validated independently against the current Jackett interface. Until end-to-end tests pass, describe both integrations as planned/experimental.

## Platform verification

A macOS manager preview does not establish that the Byparr browser engine works on macOS. The upstream browser dependency has previously reported macOS as unsupported in the development environment. The target deployment is Windows 11, so engine installation, browser startup, service operation, API calls and real challenge tests must be performed on Windows 11 before a Windows release is marked supported.

## Update procedure

For each upstream update:

1. Record the exact upstream tag/commit and date.
2. Review changes to `pyproject.toml`, endpoint routes, request/response models, environment settings and browser runtime.
3. Re-check the upstream licence and preserve source notices.
4. Build in an isolated test workspace.
5. Run Windows 11 service, browser, API, Prowlarr and Jackett regression tests.
6. Keep the previous known-good engine available for rollback.
7. Update this document and the third-party notice with the versions actually shipped.
