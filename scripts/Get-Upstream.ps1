[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LockFile = Join-Path $ProjectRoot "UPSTREAM.lock.json"
$VendorRoot = Join-Path $ProjectRoot "vendor"
$Target = Join-Path $VendorRoot "Byparr"
$TempRoot = Join-Path $env:TEMP ("byparr-source-" + [guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TempRoot "upstream.zip"

if (-not (Test-Path $LockFile)) {
    throw "UPSTREAM.lock.json was not found. Run this script from a complete project checkout."
}

$Lock = Get-Content -Raw -Path $LockFile | ConvertFrom-Json
if ($Lock.repository -ne "https://github.com/ThePhaseless/Byparr") {
    throw "Unexpected upstream repository in lock file. Stopping for safety."
}
if ($Lock.commit -notmatch '^[0-9a-f]{40}$') {
    throw "The upstream commit in UPSTREAM.lock.json is not a full 40-character commit SHA."
}

if (Test-Path $Target) {
    if (-not $Force) {
        throw "The upstream folder already exists at '$Target'. Nothing was changed. Use -Force only after backing up/removing that folder."
    }
    Remove-Item -LiteralPath $Target -Recurse -Force
}

New-Item -ItemType Directory -Path $VendorRoot -Force | Out-Null
New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null

try {
    $ArchiveUrl = "https://codeload.github.com/ThePhaseless/Byparr/zip/$($Lock.commit)"
    Write-Host "Downloading Byparr source at pinned commit $($Lock.commit)..."
    Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ZipPath

    $ExtractRoot = Join-Path $TempRoot "extract"
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractRoot -Force
    $Extracted = Get-ChildItem -LiteralPath $ExtractRoot -Directory | Select-Object -First 1
    if (-not $Extracted) {
        throw "The upstream archive did not contain the expected source folder."
    }

    $UpstreamLicense = Join-Path $Extracted.FullName "LICENSE"
    $UpstreamProject = Join-Path $Extracted.FullName "pyproject.toml"
    if (-not (Test-Path $UpstreamLicense) -or -not (Test-Path $UpstreamProject)) {
        throw "The downloaded archive is missing expected upstream files. Refusing to install it."
    }

    Move-Item -LiteralPath $Extracted.FullName -Destination $Target
    Write-Host ""
    Write-Host "Upstream source prepared:"
    Write-Host "  $Target"
    Write-Host "  Commit: $($Lock.commit)"
    Write-Host ""
    Write-Host "This script downloads source only. It does not install dependencies, start services, or modify Windows settings."
}
finally {
    if (Test-Path $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
