# Sign the Windows executable locally with Authenticode.
param(
    [string]$CertPath = $env:WINDOWS_CERT_PATH,
    [string]$CertPassword = $env:WINDOWS_CERT_PASSWORD,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $Root "dist\TradeDeskyWatcher\TradeDeskyWatcher.exe"

if (-not (Test-Path $ExePath)) {
    Write-Error "Build first: pyinstaller notification_watcher.spec"
}

if (-not $CertPath) {
    Write-Error "Set WINDOWS_CERT_PATH to your .pfx certificate path."
}

$Signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $Signtool) {
    Write-Error "signtool.exe not found. Install Windows SDK."
}

$args = @(
    "sign",
    "/fd", "SHA256",
    "/tr", $TimestampUrl,
    "/td", "SHA256",
    "/f", $CertPath,
    $ExePath
)
if ($CertPassword) {
    $args += @("/p", $CertPassword)
}

& signtool.exe @args
Write-Host "Signed $ExePath"
