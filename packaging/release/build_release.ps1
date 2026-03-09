param(
  [string]$Python = "python",
  [string]$Version = $env:OPERA_VERSION,
  [ValidateSet("x64", "x86")]
  [string]$Architecture = "x64",
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
  & powershell -ExecutionPolicy Bypass -File "packaging/windows/build_installer.ps1" -Python $Python -Version $Version -Architecture $Architecture
  if ($LASTEXITCODE -ne 0) {
    throw "Windows installer build failed."
  }
} else {
  Write-Host "Skipping Windows installer build (-SkipWindowsInstallerBuild)."
}

# 2) Assemble release folder
$relDir = Join-Path $repoRoot "dist\release\SISTEMA_OPERA_$Version"
$macDir = Join-Path $relDir "macos"
$winDir = Join-Path $relDir "windows"
$configPy = Join-Path $repoRoot "configurar_postgres.py"

if (Test-Path $relDir) { Remove-Item $relDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $macDir | Out-Null
New-Item -ItemType Directory -Force -Path $winDir | Out-Null

# Copy PostgreSQL configurator source script to release root
if (-not (Test-Path $configPy)) {
  throw "File not found: '$configPy'."
}
Copy-Item -Force $configPy $relDir

# Copy Windows installer exe (architecture-specific first)
$archInstaller = Join-Path $repoRoot ("dist\SistemaOpera_Setup_" + $Architecture + ".exe")
if (Test-Path $archInstaller) {
  Copy-Item -Force $archInstaller $winDir
} elseif (Test-Path (Join-Path $repoRoot "dist\installers\windows\*.exe")) {
  Copy-Item -Force (Join-Path $repoRoot "dist\installers\windows\*.exe") $winDir
} else {
  throw "Windows installer not found. Expected '$archInstaller' or files in dist\installers\windows\*.exe"
}

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
Write-Host "Usage: powershell -ExecutionPolicy Bypass -File packaging/release/build_release.ps1 -Python python -Version $Version -Architecture $Architecture"
