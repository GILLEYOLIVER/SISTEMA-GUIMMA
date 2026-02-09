param(
    [string]$Python = "python",
    [string]$IssPath = "packaging/windows/SISTEMA_OPERA.iss",
    [string]$Version = $env:OPERA_VERSION,
    [string]$InnoPath = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$prepareIconPath = Join-Path $repoRoot "packaging/windows/prepare_icon.py"
$buildScriptPath = Join-Path $repoRoot "packaging/build.py"
$specPath = Join-Path $repoRoot "SistemaOpera.spec"
$issFullPath = if ([System.IO.Path]::IsPathRooted($IssPath)) { $IssPath } else { Join-Path $repoRoot $IssPath }

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = "1.0.0"
}

# prepara ícone .ico (seu fluxo atual)
& $Python $prepareIconPath

# build PyInstaller Windows usando o spec
& $Python $buildScriptPath --platform windows --spec $specPath

# Inno Setup (iscc.exe)
$inno = $null
if (-not [string]::IsNullOrWhiteSpace($InnoPath)) {
    $inno = Get-Command $InnoPath -ErrorAction SilentlyContinue
} else {
    $inno = Get-Command iscc.exe -ErrorAction SilentlyContinue
}
if (-not $inno) {
    Write-Warning "Inno Setup (iscc.exe) not found. Install Inno Setup or pass -InnoPath 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'."
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
  "$issFullPath"

Write-Host "✅ EXE gerado em: $outDir"
