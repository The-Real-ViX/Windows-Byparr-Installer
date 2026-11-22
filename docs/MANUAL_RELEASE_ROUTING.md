# Manual release routing — implementation notes

This feature is being developed on `feature/manual-arr-release-routing`, based on the user-validated Build 388 checkpoint. Build 388 and its checkpoint branch are not modified.

## Why the Arr API owns the release search

Prowlarr search results are not interchangeable with Radarr/Sonarr/Lidarr release records. The Arr applications maintain their own indexer IDs, release eligibility decisions, quality profiles and download-client routing.

The supported workflow therefore uses the selected Arr application's own interactive release search and grab API. For Radarr, the implementation uses:
- `GET /api/v3/movie?term=...` to find a movie already in the library.
- `GET /api/v3/release?movieId=...` to obtain Radarr's release choices.
- `POST /api/v3/release` with only the selected result's `guid` and `indexerId` to grab that exact result.

The API key is sent only in the `X-Api-Key` header. Search results returned to the UI are reduced to safe display fields; raw download URLs and API credentials are not exposed. Opaque, short-lived, single-use handles keep internal Arr IDs and release identifiers out of the presentation layer.

## Current implementation status

The Radarr API client, focused unit tests, authenticated remote-dashboard routes and remote-dashboard movie/release selection UI are implemented on this feature branch.

The remote workflow provides:
1. Movie search within the existing Radarr library.
2. A read-only list of Radarr's own releases for the selected movie.
3. Release details including quality, size, indexer, protocol and seeders.
4. No selection action for releases Radarr marks as unapproved.
5. An explicit confirmation naming the movie, exact release, quality, size and Radarr's configured download-client destination.
6. A separate grab request only after confirmation.

Searching, opening a result, or selecting a release does not submit a download. Cancel leaves Radarr untouched. A failed or stale selected release is reported; there is no automatic alternate grab. The approval flag defaults to false when Radarr omits it, so an incomplete response fails closed.

**Not yet verified:** a fresh Windows installation and an end-to-end test against the user's real Radarr instance and download client. The feature is not merged into the default branch. The native desktop Manager does not yet provide this manual Radarr movie/release selection screen; the first UI is in the private Tailscale remote dashboard.

## Next work

1. Test the remote Radarr workflow on Windows 11 against a real Radarr instance, including cancel, approved/unapproved releases and successful grab.
2. Add equivalent movie/release selection to the native desktop Manager if the remote workflow passes.
3. Only after Radarr has passed real-device testing, extend the same pattern to Sonarr and Lidarr using their own API contracts. TV selection needs series/episode context; music selection needs artist/album context. Do not infer these IDs from Prowlarr search results.

## Stability boundaries

- Do not modify the Build 388 checkpoint.
- Do not update Byparr or dependency pins for this feature.
- Preserve the existing Prowlarr direct-grab workflow unchanged.
- Do not merge this feature into the default branch until CI and user testing pass.
