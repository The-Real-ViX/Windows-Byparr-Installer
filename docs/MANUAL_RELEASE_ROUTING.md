# Manual release routing — implementation notes

This feature is being developed on `feature/manual-arr-release-routing`, based on the user-validated Build 388 checkpoint. Build 388 and its checkpoint branch are not modified.

## Why the Arr API owns the release search

Prowlarr search results are not interchangeable with Radarr/Sonarr/Lidarr release records. The Arr applications maintain their own indexer IDs, release eligibility decisions, quality profiles and download-client routing.

The supported workflow therefore uses the selected Arr application's own interactive release search and grab API. For Radarr, the initial implementation uses:
- `GET /api/v3/movie?term=...` to find a movie already in the library.
- `GET /api/v3/release?movieId=...` to obtain Radarr's release choices.
- `POST /api/v3/release` with only the selected result's `guid` and `indexerId` to grab that exact result.

The API key is sent only in the `X-Api-Key` header. Search results returned to the UI are reduced to safe display fields; raw download URLs and API credentials are not exposed. Opaque, short-lived, single-use handles keep internal Arr IDs and release identifiers out of the presentation layer.

## Current milestone

The Radarr API client and focused unit tests are being added first. The desktop and Tailscale dashboard interfaces must then provide:
1. Movie search and explicit movie selection.
2. A read-only list of Radarr's own releases.
3. Explicit release selection.
4. A confirmation dialog naming the movie, release and Radarr destination.
5. A separate explicit grab action after confirmation.

Searching, opening a result, or selecting a release must never submit a download. Cancel must leave Radarr untouched. A failed or stale selected release must be reported; there is no automatic alternate grab.

## Later work

After the Radarr flow passes CI and user testing, extend the same pattern to Sonarr and Lidarr using their own API contracts. TV selection needs series/episode context; music selection needs artist/album context. Do not infer these IDs from Prowlarr search results.

## Stability boundaries

- Do not modify the Build 388 checkpoint.
- Do not update Byparr or dependency pins for this feature.
- Preserve the existing Prowlarr direct-grab workflow unchanged.
- Do not merge this feature into the default branch until CI and user testing pass.
