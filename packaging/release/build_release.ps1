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

if ([string]::IsNullOrWhiteSpace($Version)) { $Version = "1.0.0" }

function Resolve-FirstExisting([string[]]$paths) {
  foreach ($p in $paths) { if ($p -and (Test-Path $p)) { return $p } }
  return $null
}

if (-not $SkipWindowsInstallerBuild) {
  & powershell -ExecutionPolicy Bypass -File "packaging/windows/build_installer.ps1" -Python $Python -Version $Version -Architecture $Architecture
  if ($LASTEXITCODE -ne 0) { throw "Windows installer build failed." }
} else {
  Write-Host "Skipping Windows installer build (-SkipWindowsInstallerBuild)."
}

# Ensure CONFIGURAR_POSTGRES.exe (without rebuilding official installer)
& powershell -ExecutionPolicy Bypass -File "packaging/windows/build_unified_package.ps1" -Python $Python -Version $Version -Architecture $Architecture -SkipInstallerBuild
if ($LASTEXITCODE -ne 0) { throw "Failed to build CONFIGURAR_POSTGRES.exe via build_unified_package.ps1" }

$relDir = Join-Path $repoRoot "dist\release\SISTEMA_OPERA_$Version"
$macDir = Join-Path $relDir "macos"
$winDir = Join-Path $relDir "windows"

if (Test-Path $relDir) { Remove-Item $relDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $macDir | Out-Null
New-Item -ItemType Directory -Force -Path $winDir | Out-Null

# WINDOWS folder target: official installer + CONFIGURAR_BANCO + CONFIGURAR_POSTGRES + SCRIPTS
$installerExe = Resolve-FirstExisting @(
  (Join-Path $repoRoot ("dist\SistemaOpera_Setup_" + $Architecture + ".exe")),
  (Join-Path $repoRoot "dist\SistemaOpera_Setup.exe")
)
if (-not $installerExe) { throw "Official installer not found in dist/." }
Copy-Item -Force $installerExe $winDir

$configBancoExe = Resolve-FirstExisting @(
  (Join-Path $repoRoot "dist\SistemaOpera\CONFIGURAR_BANCO.exe"),
  (Join-Path $repoRoot "dist\windows\CONFIGURAR_BANCO.exe")
)
if (-not $configBancoExe) { throw "CONFIGURAR_BANCO.exe not found." }
Copy-Item -Force $configBancoExe $winDir

$configPostgresExe = Resolve-FirstExisting @(
  (Join-Path $repoRoot ("dist\installers\unified\SISTEMA_OPERA_" + $Version + "_" + $Architecture + "\CONFIGURAR_POSTGRES.exe")),
  (Join-Path $repoRoot "dist\SistemaOpera\CONFIGURAR_POSTGRES.exe")
)
if (-not $configPostgresExe) { throw "CONFIGURAR_POSTGRES.exe not found." }
Copy-Item -Force $configPostgresExe $winDir

$scriptsDir = Join-Path $repoRoot "SCRIPTS"
if (-not (Test-Path $scriptsDir)) { throw "SCRIPTS directory not found: $scriptsDir" }
Copy-Item -Recurse -Force $scriptsDir (Join-Path $winDir "SCRIPTS")
Copy-Item -Recurse -Force $scriptsDir (Join-Path $macDir "SCRIPTS")

# MAC folder target: dmg + launchers similar to windows tools
$macDmg = Join-Path $repoRoot "dist\installers\macos\SISTEMA_OPERA_${Version}_macOS.dmg"
if (Test-Path $macDmg) { Copy-Item -Force $macDmg $macDir }

$configBancoPy = Join-Path $repoRoot "PAGINAS_DO_SISTEMA\SETUP_BANCO.py"
$configPostgresPy = Join-Path $repoRoot "configurar_postgres.py"
if (Test-Path $configBancoPy) { Copy-Item -Force $configBancoPy (Join-Path $macDir "CONFIGURAR_BANCO.py") }
if (Test-Path $configPostgresPy) { Copy-Item -Force $configPostgresPy (Join-Path $macDir "CONFIGURAR_POSTGRES.py") }

$launcherBanco = @(
  "#!/usr/bin/env bash",
  "cd \"\$(dirname \"\$0\")\"",
  "python3 CONFIGURAR_BANCO.py"
)
$launcherPostgres = @(
  "#!/usr/bin/env bash",
  "cd \"\$(dirname \"\$0\")\"",
  "python3 CONFIGURAR_POSTGRES.py"
)
Set-Content -Path (Join-Path $macDir "CONFIGURAR_BANCO.command") -Value $launcherBanco -Encoding UTF8
Set-Content -Path (Join-Path $macDir "CONFIGURAR_POSTGRES.command") -Value $launcherPostgres -Encoding UTF8

$zipOut = Join-Path $repoRoot "dist\SISTEMA_OPERA_${Version}_INSTALLER.zip"
if (Test-Path $zipOut) { Remove-Item $zipOut -Force }

# ZIP must mirror exactly the WINDOWS folder contents
$zipSource = Join-Path $winDir "*"
Compress-Archive -Path $zipSource -DestinationPath $zipOut -Force

Write-Host "Package generated: $zipOut"
Write-Host "ZIP content mirrors the WINDOWS folder exactly."
Write-Host "Windows folder: SCRIPTS + CONFIGURAR_BANCO.exe + CONFIGURAR_POSTGRES.exe + installer"
Write-Host "macos folder: SCRIPTS + CONFIGURAR_BANCO.command + CONFIGURAR_POSTGRES.command + DMG (if available)"
