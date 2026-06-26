# Build unified Windows output folder with:
# 1) Sistema Guimma installer
# 2) CONFIGURAR_POSTGRES.exe (from configurar_postgres.py) using PG_ICON.ico

param(
    [string]$Python = "python",
    [string]$Version = "1.0.0",
    [ValidateSet("x64", "x86")]
    [string]$Architecture = "x64",
    [switch]$SkipInstallerBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try { chcp 65001 | Out-Null } catch { }
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot


function Get-PythonArch([string]$PyCmd) {
    $arch = & $PyCmd -c "import struct; print('x64' if struct.calcsize('P')*8==64 else 'x86')"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($arch)) {
        throw "Failed to detect Python architecture from '$PyCmd'."
    }
    return $arch.Trim()
}


$unifiedDir = Join-Path $repoRoot ("dist\SISTEMA_OPERA_" + $Version + "_" + $Architecture)
$buildDir = Join-Path $repoRoot "build\pyi_configurar_postgres"
$configScript = Join-Path $repoRoot "configurar_postgres.py"
$pgIcon = Join-Path $repoRoot "PG_ICON.ico"

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  SISTEMA GUIMMA - UNIFIED BUILD (INSTALLER + CONFIGURAR_POSTGRES)" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

$pythonArch = Get-PythonArch $Python
Write-Host "Python architecture detected: $pythonArch" -ForegroundColor Cyan
if ($pythonArch -ne $Architecture) {
    throw "Requested architecture '$Architecture' but Python is '$pythonArch'. Use a matching Python interpreter."
}


if (-not (Test-Path $configScript)) {
    throw "Missing file: $configScript"
}
if (-not (Test-Path $pgIcon)) {
    throw "Missing icon: $pgIcon"
}

if (-not $SkipInstallerBuild) {
    Write-Host "`n[1/3] Building main Sistema Guimma installer..." -ForegroundColor Green
    & powershell -ExecutionPolicy Bypass -File "packaging/windows/build_installer.ps1" -Python $Python -Version $Version -Architecture $Architecture
    if ($LASTEXITCODE -ne 0) { throw "Failed building main installer." }
} else {
    Write-Host "`n[1/3] Skipping main installer build (-SkipInstallerBuild)." -ForegroundColor Yellow
}

Write-Host "`n[2/3] Building CONFIGURAR_POSTGRES.exe with PG_ICON.ico ($Architecture)..." -ForegroundColor Green
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
New-Item -ItemType Directory -Force -Path $unifiedDir | Out-Null

& $Python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "CONFIGURAR_POSTGRES" `
  --icon "$pgIcon" `
  --distpath "$unifiedDir" `
  --workpath "$buildDir" `
  --specpath "build" `
  --hidden-import "tkinter" `
  --hidden-import "customtkinter" `
  --hidden-import "winreg" `
  --hidden-import "ctypes" `
  "$configScript"

if ($LASTEXITCODE -ne 0) {
    throw "Failed building CONFIGURAR_POSTGRES.exe"
}

$configExe = Join-Path $unifiedDir "CONFIGURAR_POSTGRES.exe"
if (-not (Test-Path $configExe)) {
    throw "CONFIGURAR_POSTGRES.exe not found: $configExe"
}

Write-Host "`n[3/3] Consolidating artifacts into one folder..." -ForegroundColor Green

$installerCopied = $false
$installerCandidates = @(
    (Join-Path $repoRoot ("dist\SistemaOpera_Setup_" + $Architecture + ".exe")),
    (Join-Path $repoRoot "dist\installers\windows\SISTEMA_OPERA_Setup.exe")
)

foreach ($installer in $installerCandidates) {
    if (Test-Path $installer) {
        Copy-Item -Force $installer $unifiedDir
        $installerCopied = $true
    }
}

$windowsInstallerDir = Join-Path $repoRoot "dist\installers\windows"
if (Test-Path $windowsInstallerDir) {
    $winInstallers = Get-ChildItem -Path $windowsInstallerDir -Filter "*.exe" -File -ErrorAction SilentlyContinue
    if ($winInstallers) {
        $winInstallers | ForEach-Object { Copy-Item -Force $_.FullName $unifiedDir }
        $installerCopied = $true
    }
}

if (-not $installerCopied) {
    Write-Warning "No Sistema Guimma installer EXE found to copy."
}

Copy-Item -Force $pgIcon (Join-Path $unifiedDir "PG_ICON.ico")

# Include CONFIGURAR_BANCO.exe and SCRIPTS in unified root folder
$configBancoCandidates = @(
    (Join-Path $repoRoot "dist\SistemaOpera\CONFIGURAR_BANCO.exe"),
    (Join-Path $repoRoot "dist\windows\CONFIGURAR_BANCO.exe")
)
$configBancoExe = $null
foreach ($c in $configBancoCandidates) {
    if (Test-Path $c) { $configBancoExe = $c; break }
}
if ($configBancoExe) {
    Copy-Item -Force $configBancoExe $unifiedDir
} else {
    Write-Warning "CONFIGURAR_BANCO.exe not found to copy into unified folder."
}

$scriptsDir = Join-Path $repoRoot "SCRIPTS"
if (Test-Path $scriptsDir) {
    Copy-Item -Recurse -Force $scriptsDir (Join-Path $unifiedDir "SCRIPTS")
} else {
    Write-Warning "SCRIPTS folder not found to copy into unified folder."
}

Write-Host "`nBuild finished successfully." -ForegroundColor Green
Write-Host "Output folder: $unifiedDir" -ForegroundColor Green
Write-Host "`nUsage:" -ForegroundColor Cyan
Write-Host ('powershell -ExecutionPolicy Bypass -File packaging/windows/build_unified_package.ps1 -Python python -Version ' + $Version + ' -Architecture ' + $Architecture) -ForegroundColor White
