# Byparr Manager v0.4.0 beta testing guide

This candidate is intended for controlled testing on Windows 11 x64 and the owner's private Tailscale network. This guide distinguishes checks actually completed on a specific build from checks that remain outstanding.

## Recorded real-world validation — Build 388

**Test date:** 2026-11-19  
**Build:** 388 — commit fd994b6556357a48cba618e7990c05ed39accda9  
**Environment:** One Windows 11 PC and an iPad connected through the private Tailscale network. Results below are maintainer-reported; they are not a broad compatibility assessment or independent security test.

- [x] Manager launched successfully (interface version 0.4).
- [x] Remote dashboard enabled on the Windows PC's Tailscale address and login succeeded from the iPad.
- [x] Bundled Byparr engine started and its local API became ready (HTTP 200).
- [x] Radarr connected (6.4.4.10685; HTTP 200).
- [x] Sonarr connected (4.0.20.3014; HTTP 200).
- [x] Prowlarr connected (HTTP 200).
- [x] Lidarr connected (3.1.6.5079; HTTP 200).
- [x] qBittorrent connection test passed through Prowlarr (HTTP 200).
- [x] Browser Health passed (HTTP 200; reported healthy, version unknown).
- [x] Remote Audio/Music search returned 50 results.
- [x] Remote TV Shows search completed and returned zero results; this was a no-results response, not an API failure.
- [x] A selected release was accepted by Prowlarr and the maintainer confirmed qBittorrent worked successfully.
- [x] No automatic application log folder or file appeared on the Desktop.
- [x] The in-app Logs page continued to display activity.
- [x] The iPad remote search and release-grab workflow was repeated successfully on Build 388.

This confirms the reported Build 388 workflows on this test setup only. It does not establish support for every Windows configuration, indexer, or tailnet setup.

## Further desktop checks

- [ ] Start, stop and restart the Byparr engine repeatedly.
- [ ] Open the Logs page and use the explicit Export logs action.
- [ ] Run an indexer test in Prowlarr using Byparr.
- [ ] Close and reopen the Manager; check that settings persist.
- [ ] Confirm uninstall/reinstall behaviour and the optional full-cleanup prompt.

## Further private Tailscale checks

Only perform these checks on devices in the intended private tailnet. Do not expose the dashboard port to the public internet.

- [ ] Confirm logout requires authentication again.
- [ ] Disable remote access and confirm the remote endpoint stops responding.
- [ ] Confirm access is limited to intended tailnet devices using appropriate Tailscale ACLs.

## When reporting a problem

Use the Bug report form. Include the app version/build, Windows version, exact steps, expected result, actual result and relevant redacted logs. Say whether the issue happens every time or only sometimes.

**Never attach secrets.** Remove API keys, passwords, cookies, tokens, private tracker URLs, personal names, local file paths and IP addresses before posting logs or screenshots.

## Beta expectations

This project is maintained by one person in spare time. Reports are welcome, but responses and fixes are not guaranteed to be immediate. This is not a public-internet remote-access product and has not undergone an independent penetration test.
