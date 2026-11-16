# Upstream source workflow

The original Byparr engine is not rewritten or silently patched by this project. The exact source revision is recorded in [UPSTREAM.lock.json](../UPSTREAM.lock.json).

## Prepare the pinned source

From a PowerShell window opened in the project root:

```powershell
.\scripts\Get-Upstream.ps1
```

The script downloads the archive for the exact 40-character commit in the lock file and prepares it under `vendor\Byparr`. It checks for the upstream licence and project metadata before moving the source into place.

The script:
- Does not run as administrator.
- Does not install Python or browser dependencies.
- Does not register or start a Windows service.
- Does not change firewall or network settings.
- Refuses to overwrite an existing `vendor\Byparr` folder unless `-Force` is explicitly supplied.

Use `-Force` only after preserving any local changes you need. The download is an archive snapshot, not a Git working copy; upstream history remains available at the original repository.

## Updating the pin

1. Inspect upstream releases and commits at https://github.com/ThePhaseless/Byparr.
2. Choose a specific commit SHA, not a floating branch name.
3. Review its licence, Python requirement, dependencies, API models, endpoints and browser runtime changes.
4. Update `UPSTREAM.lock.json` to the reviewed commit.
5. Prepare it in a clean test checkout.
6. Run Windows 11 browser, API, service and Prowlarr regression tests.
7. Only then mark the revision as supported and publish the corresponding source/build.

Never auto-promote an upstream commit directly onto a user's working installation. Keep the last known-good version available for rollback.
