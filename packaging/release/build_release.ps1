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

# 1) Gera instalador Windows (EXE Setup), a menos que o usuário queira reaproveitar artefato já existente
if (-not $SkipWindowsInstallerBuild) {
  & powershell -ExecutionPolicy Bypass -File packaging/windows/build_installer.ps1 -Python $Python -Version $Version -InnoPath $InnoPath -SkipAppBuild:$SkipAppBuild
} else {
  Write-Host "ℹ️ Pulando geração do instalador Windows (-SkipWindowsInstallerBuild)."
}

# 2) Monta pasta release com os 2 (se o mac dmg já existir, ele entra também)
$relDir = Join-Path $repoRoot "dist\release\SISTEMA_OPERA_$Version"
$macDir = Join-Path $relDir "macos"
$winDir = Join-Path $relDir "windows"

if (Test-Path $relDir) { Remove-Item $relDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $macDir | Out-Null
New-Item -ItemType Directory -Force -Path $winDir | Out-Null

# Copia EXE
$winInstallerPattern = Join-Path $repoRoot "dist\installers\windows\*.exe"
if (-not (Test-Path $winInstallerPattern)) {
  throw "Instalador Windows não encontrado em '$winInstallerPattern'. Execute o build do instalador e confirme o output."
}
Copy-Item -Force $winInstallerPattern $winDir

# Copia DMG se já existir (por exemplo, você rodou no Mac e trouxe o arquivo)
$macDmg = Join-Path $repoRoot "dist\installers\macos\SISTEMA_OPERA_${Version}_macOS.dmg"
if (Test-Path $macDmg) {
  Copy-Item -Force $macDmg $macDir
}

# 3) ZIP único
$zipOut = Join-Path $repoRoot "dist\SISTEMA_OPERA_${Version}_INSTALLER.zip"
if (Test-Path $zipOut) { Remove-Item $zipOut -Force }

Compress-Archive -Path $relDir -DestinationPath $zipOut -Force
Write-Host "✅ Pacote único gerado: $zipOut"
