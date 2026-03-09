# Gera em uma única pasta:
# 1) instalador do Sistema OPERA
# 2) executável de configurar_postgres.py com ícone PG_ICON.ico

param(
    [string]$Python = "python",
    [string]$Version = "1.0.0",
    [switch]$SkipInstallerBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path
Set-Location $repoRoot

$unifiedDir = Join-Path $repoRoot "dist\installers\unified\SISTEMA_OPERA_$Version"
$buildDir = Join-Path $repoRoot "build\pyi_configurar_postgres"
$configScript = Join-Path $repoRoot "configurar_postgres.py"
$pgIcon = Join-Path $repoRoot "PG_ICON.ico"

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  OPERA - BUILD UNIFICADO (INSTALADOR + CONFIGURAR_POSTGRES)" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

if (-not (Test-Path $configScript)) {
    throw "Arquivo não encontrado: $configScript"
}
if (-not (Test-Path $pgIcon)) {
    throw "Ícone não encontrado: $pgIcon"
}

if (-not $SkipInstallerBuild) {
    Write-Host "`n[1/3] Gerando instalador principal do Sistema OPERA..." -ForegroundColor Green
    & powershell -ExecutionPolicy Bypass -File "packaging/windows/build_installer.ps1" -Python $Python -Version $Version
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar instalador principal." }
} else {
    Write-Host "`n[1/3] Pulando build do instalador principal (-SkipInstallerBuild)." -ForegroundColor Yellow
}

Write-Host "`n[2/3] Gerando CONFIGURAR_POSTGRES.exe com ícone PG_ICON.ico..." -ForegroundColor Green
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

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
    throw "Falha ao gerar CONFIGURAR_POSTGRES.exe"
}

$configExe = Join-Path $unifiedDir "CONFIGURAR_POSTGRES.exe"
if (-not (Test-Path $configExe)) {
    throw "Executável não encontrado: $configExe"
}

Write-Host "`n[3/3] Consolidando artefatos na pasta única..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $unifiedDir | Out-Null

$installerCandidates = @(
    (Join-Path $repoRoot "dist\SistemaOpera_Setup.exe"),
    (Join-Path $repoRoot "dist\installers\windows\SISTEMA_OPERA_Setup.exe")
)

$installerCopied = $false
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
    Write-Warning "Nenhum instalador do OPERA encontrado para copiar."
}

Copy-Item -Force $pgIcon (Join-Path $unifiedDir "PG_ICON.ico")

Write-Host "`n✅ Build unificado concluído com sucesso!" -ForegroundColor Green
Write-Host "📁 Pasta final: $unifiedDir" -ForegroundColor Green
Write-Host "`nComando de uso:" -ForegroundColor Cyan
Write-Host "powershell -ExecutionPolicy Bypass -File packaging/windows/build_unified_package.ps1 -Python python -Version $Version" -ForegroundColor White
