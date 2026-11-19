from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

PROJECT = Path("vendor/Byparr")
PYPROJECT = PROJECT / "pyproject.toml"

replacements = {
    '"fastapi[standard]==0.162.*"': '"fastapi[standard]==0.163.*"',
    '"playwright==1.64.*"': '"playwright==1.65.*"',
    '"pytest-asyncio==1.4.*"': '"pytest-asyncio==1.5.*"',
}

text = PYPROJECT.read_text(encoding="utf-8")
for old, new in replacements.items():
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {old!r} in {PYPROJECT}; found {count}.")
    text = text.replace(old, new, 1)
PYPROJECT.write_text(text, encoding="utf-8")

subprocess.run(
    [
        "uv",
        "lock",
        "--upgrade-package",
        "fastapi",
        "--upgrade-package",
        "playwright",
        "--upgrade-package",
        "pytest-asyncio",
    ],
    cwd=PROJECT,
    check=True,
)

with (PROJECT / "uv.lock").open("rb") as lock_file:
    lock = tomllib.load(lock_file)

versions = {
    package["name"]: package["version"]
    for package in lock.get("package", [])
    if package["name"] in {"fastapi", "playwright", "pytest-asyncio"}
}
expected = {"fastapi", "playwright", "pytest-asyncio"}
if set(versions) != expected:
    raise SystemExit(f"Lockfile is missing expected packages: {versions}")
print("Isolated upstream dependency candidate:")
for name in sorted(versions):
    print(f"  {name}=={versions[name]}")
