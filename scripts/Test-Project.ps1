$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$LockPath = Join-Path $Root "UPSTREAM.lock.json"
$LicensePath = Join-Path $Root "LICENSE"
$ReadmePath = Join-Path $Root "README.md"
$FetchScript = Join-Path $PSScriptRoot "Get-Upstream.ps1"

foreach ($Path in @($LockPath, $LicensePath, $ReadmePath, $FetchScript)) {
    if (-not (Test-Path $Path)) {
        throw "Required project file is missing: $Path"
    }
}

$Lock = Get-Content -Raw $LockPath | ConvertFrom-Json
if ($Lock.commit -notmatch '^[0-9a-f]{40}$') {
    throw "UPSTREAM.lock.json must contain a full 40-character commit SHA."
}
if ($Lock.license -ne "GPL-3.0") {
    throw "Unexpected upstream licence marker. Review before continuing."
}

$Tokens = $null
$ParseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $FetchScript,
    [ref]$Tokens,
    [ref]$ParseErrors
) | Out-Null

if ($Errors.Count -gt 0) {
    $Errors | ForEach-Object { Write-Error $_.Message }
    throw "PowerShell syntax validation failed."
}

Write-Host "Project integrity checks passed."
Write-Host "Pinned Byparr commit: $($Lock.commit)"
Write-Host "Note: this does not test Byparr runtime, browser solving, Windows service behaviour, or Prowlarr integration."
