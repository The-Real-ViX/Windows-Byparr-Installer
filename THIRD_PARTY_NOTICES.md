# Third-party notices

## Byparr engine

- Project: [Byparr](https://github.com/ThePhaseless/Byparr)
- Author/maintainer: ThePhaseless
- Pinned source revision: `c81385f59ec978ef81909a273e514ca6d9ace2a9` (see [UPSTREAM.lock.json](UPSTREAM.lock.json))
- Licence: GNU General Public License, version 3 (GPL-3.0)
- The full licence text is provided in [LICENSE](LICENSE).
- The upstream source is fetched during the Windows build by `scripts/Get-Upstream.ps1`; the exact corresponding source revision must remain available to recipients of any distributed binary.
- Copyright notices and licence headers in upstream source files must remain intact.

This repository is an independent Windows-focused installer and manager project. It is not an official Byparr release and ThePhaseless is not represented as endorsing it.

## Bundled components — inventory not yet complete

**Important: this file is not yet a complete binary-distribution notice. Do not publish a packaged installer as a public release until this inventory and the corresponding licence/source obligations have been completed and checked.**

The Windows build workflow packages more than the Manager's own Python code. It currently includes or downloads components such as:

- The Manager and its Python dependencies, including PySide6/Qt, HTTPX, Keyring and Windows credential support.
- The Byparr engine and its locked Python dependency tree (see the pinned upstream `pyproject.toml` and `uv.lock`).
- Invisible Playwright and its fetched browser runtime.
- Playwright-related packages and supporting libraries.
- PyInstaller and Inno Setup build/installer tooling (verify whether each is redistributed in the final installer or used only at build time).

The exact versions, copyright holders, licence identifiers, licence texts, source locations, and redistribution conditions for every component actually present in the installer still need to be generated from the final packaged build. Build-time-only tools should be clearly distinguished from components shipped to users.

## Distribution checklist

- [ ] Generate a software bill of materials from the exact Windows release build.
- [ ] Verify the licence and redistribution terms for every shipped Python package and native library.
- [ ] Identify the exact browser runtime build and confirm its redistribution terms.
- [ ] Include required copyright notices and full licence texts for shipped components.
- [ ] Make the exact corresponding source for GPL-covered distributed binaries available, including the pinned Byparr source and project modifications.
- [ ] Verify that the release assets and source links satisfy the applicable licence requirements.
- [ ] Record the exact upstream commit, app version, build number, and release date.
- [ ] Publish SHA-256 checksums for release assets.
- [ ] Re-run the Windows installer and integration smoke tests against the exact release candidate.
