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
$StagedSource = Join-Path $TempRoot "staged-Byparr"
$Backup = $null

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

if ((Test-Path $Target) -and -not $Force) {
    throw "The upstream folder already exists at '$Target'. Nothing was changed. Use -Force to replace it after the new source has been downloaded and validated."
}

New-Item -ItemType Directory -Path $VendorRoot -Force | Out-Null
New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null

try {
    $ArchiveUrl = "https://codeload.github.com/ThePhaseless/Byparr/zip/$($Lock.commit)"
    Write-Host "Downloading Byparr source at pinned commit $($Lock.commit)..."
    Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ZipPath

    $ExtractRoot = Join-Path $TempRoot "extract"
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractRoot -Force
    $ExtractedFolders = @(Get-ChildItem -LiteralPath $ExtractRoot -Directory)
    if ($ExtractedFolders.Count -ne 1) {
        throw "The upstream archive did not contain exactly one source folder. Refusing to install it."
    }

    $Extracted = $ExtractedFolders[0]
    $UpstreamLicense = Join-Path $Extracted.FullName "LICENSE"
    $UpstreamProject = Join-Path $Extracted.FullName "pyproject.toml"
    if (-not (Test-Path $UpstreamLicense) -or -not (Test-Path $UpstreamProject)) {
        throw "The downloaded archive is missing expected upstream files. Refusing to install it."
    }

    # Stage the validated download before touching any existing vendor folder.
    Move-Item -LiteralPath $Extracted.FullName -Destination $StagedSource

    if (Test-Path $Target) {
        $Backup = "$Target.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Move-Item -LiteralPath $Target -Destination $Backup
        Write-Host "Existing upstream folder preserved at: $Backup"
    }

    try {
        Move-Item -LiteralPath $StagedSource -Destination $Target
    }
    catch {
        # If replacement fails, put the previous folder back where it was.
        if ($Backup -and (Test-Path $Backup) -and -not (Test-Path $Target)) {
            Move-Item -LiteralPath $Backup -Destination $Target
            Write-Warning "The replacement failed. The previous upstream folder has been restored."
        }
        throw
    }

    Write-Host ""
    Write-Host "Upstream source prepared:"
    Write-Host "  $Target"
    Write-Host "  Commit: $($Lock.commit)"
    if ($Backup) {
        Write-Host "  Previous source backup: $Backup"
    }
    Write-Host ""
    Write-Host "This script downloads source only. It does not install dependencies, start services, or modify Windows settings."
}
finally {
    if (Test-Path $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
