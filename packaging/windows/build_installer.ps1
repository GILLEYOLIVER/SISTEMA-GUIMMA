param(
    [string]$Python = "python",
    [string]$IssPath = "packaging/windows/SISTEMA_OPERA.iss",
    [string]$Version = $env:OPERA_VERSION
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = "1.0.0"
}

# prepara ícone .ico (seu fluxo atual)
& $Python packaging/windows/prepare_icon.py

# build PyInstaller Windows usando o spec
& $Python packaging/build.py --platform windows --spec "$repoRoot\SistemaOpera.spec"

# Inno Setup (iscc.exe)
$inno = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $inno) {
    Write-Warning "Inno Setup (iscc.exe) not found. Install Inno Setup and rerun to create the installer."
    exit 1
}

# saída padrão (pode mudar)
$outDir = Join-Path $repoRoot "dist\installers\windows"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# passa defines pro .iss (versão + output dir + nome do instalador)
& $inno `
  "/DAppVersion=$Version" `
  "/DOutputDir=$outDir" `
  "/DOutputBaseFilename=SISTEMA_OPERA_${Version}_Windows_Setup" `
  "$IssPath"

Write-Host "✅ EXE gerado em: $outDir"
