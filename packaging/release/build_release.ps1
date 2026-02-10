param(
  [string]$Python = "python",
  [string]$Version = $env:OPERA_VERSION,
  [string]$InnoPath = "",
  [switch]$SkipAppBuild,
  [switch]$SkipWindowsInstallerBuild
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($Version)) {
  $Version = "1.0.0"
}

# 1) Build Windows installer (setup exe), unless user wants to reuse existing artifact
if (-not $SkipWindowsInstallerBuild) {
  & powershell -ExecutionPolicy Bypass -File packaging/windows/build_installer.ps1 -Python $Python -Version $Version -InnoPath $InnoPath -SkipAppBuild:$SkipAppBuild
} else {
  Write-Host "Skipping Windows installer build (-SkipWindowsInstallerBuild)."
}

# 2) Assemble release folder
$relDir = Join-Path $repoRoot "dist\release\SISTEMA_OPERA_$Version"
$macDir = Join-Path $relDir "macos"
$winDir = Join-Path $relDir "windows"

if (Test-Path $relDir) { Remove-Item $relDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $macDir | Out-Null
New-Item -ItemType Directory -Force -Path $winDir | Out-Null

# Copy Windows installer exe
$winInstallerPattern = Join-Path $repoRoot "dist\installers\windows\*.exe"
if (-not (Test-Path $winInstallerPattern)) {
  throw "Windows installer not found at '$winInstallerPattern'. Build the installer and confirm output path."
}
Copy-Item -Force $winInstallerPattern $winDir

# Copy macOS dmg if present
$macDmg = Join-Path $repoRoot "dist\installers\macos\SISTEMA_OPERA_${Version}_macOS.dmg"
if (Test-Path $macDmg) {
  Copy-Item -Force $macDmg $macDir
}

# 3) Create single ZIP
$zipOut = Join-Path $repoRoot "dist\SISTEMA_OPERA_${Version}_INSTALLER.zip"
if (Test-Path $zipOut) { Remove-Item $zipOut -Force }

Compress-Archive -Path $relDir -DestinationPath $zipOut -Force
Write-Host "Package generated: $zipOut"
