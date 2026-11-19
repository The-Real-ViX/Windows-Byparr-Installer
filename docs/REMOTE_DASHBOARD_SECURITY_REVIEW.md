# Remote Dashboard Security Review

**Review scope:** Static review of the opt-in Tailscale remote dashboard and its Prowlarr search/grab path. This is an internal engineering review, not an independent penetration test or formal security certification.

## Controls implemented

- Remote service is opt-in and binds only to a configured Tailscale IPv4 CGNAT or Tailscale IPv6 ULA address; it does not bind to all interfaces.
- The Byparr API remains bound to localhost. Prowlarr API credentials remain on the Windows host and are sent only from the Manager backend to Prowlarr.
- Remote login uses a salted PBKDF2-HMAC-SHA256 verifier (600,000 iterations) and a minimum 14-character password. The password itself is not persisted.
- Login failures are rate-limited per Tailscale source IP. Request bodies are bounded to 8 KiB and JSON content type is required for non-empty bodies.
- Requests are checked against the configured Host header; browser POST requests must carry a matching same-origin Origin.
- Authenticated POST actions require a session-bound CSRF token. Session cookies are HttpOnly and SameSite=Strict; sessions expire after 30 minutes of inactivity and are capped.
- Dashboard scripts use a per-response CSP nonce; inline event-handler attributes are not used.
- Search results expose only display fields and opaque, short-lived server-side grab handles. Raw download URLs, magnet links, and Prowlarr API keys are not sent to the browser.
- Remote audit logs record login, logout, session expiry, actions, searches, and grab outcomes. Common credential patterns, bearer tokens, URL credentials, and API-key query parameters are redacted before log display.

## Important operating limits

- The dashboard uses HTTP on the Tailscale address, not application-level HTTPS. Tailscale encrypts traffic between tailnet devices. Do not use router port forwarding, Tailscale Funnel, public reverse proxies, or expose this port outside the tailnet.
- Keep Tailscale device access restricted with tailnet ACLs and use a unique, strong dashboard password. A compromised device already on the tailnet is within the network trust boundary.
- The password verifier and salt are stored in the current user's application settings. The verifier is deliberately slow and salted, but a local attacker with access to the Windows user profile could attempt offline password guesses.
- Login rate-limit state is in memory and resets when the Manager restarts.
- The Python standard-library threaded HTTP server is intentionally small and is not a general-purpose internet-facing web server.
- No independent penetration test has been performed. Treat the feature as a private beta, not a hardened public-facing service.

## Release gate

A private beta build may be supplied for controlled testing on the owner's tailnet after all current CI jobs and the Windows packaging build pass.

A public binary beta release is **not approved by this review**. The repository's third-party dependency and bundled-runtime licence inventory, notices, and redistribution obligations have not yet been completed. Do not publish a public installer or portable binary until that separate packaging/licensing review is complete.

## Verification still required after security changes

- Install the newly built Windows package and confirm the desktop app starts.
- Confirm Tailscale login, dashboard refresh, engine controls, Prowlarr diagnostics, category search, and release grab from the iPad.
- Confirm the selected release reaches qBittorrent.
- Keep Build 130 and its protected checkpoint unchanged as the rollback baseline.
