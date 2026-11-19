# Byparr Manager v0.5.0-beta

## Added

- Optional Tailscale remote access for the Byparr API.
- Tailscale IPv4 discovery through the installed Tailscale CLI.
- The engine binds to the detected Tailscale IPv4 address when remote access is enabled, rather than listening on all network interfaces.
- Settings controls to enable remote access and refresh the detected Tailscale address.
- Documentation covering tailnet access policy, local *arr integration addresses, and security limitations.

## Security and limitations

- Tailscale remote access is disabled by default; loopback/local API binding remains the default configuration.
- The Byparr API does not gain application-level username/password authentication from this feature. Access must be restricted using Tailscale's access policy.
- The Windows Manager must remain open because it currently supervises the Byparr engine process.
- Remote connectivity and Windows Firewall behaviour still require real-world testing on the target Windows 11 PC.
