param(
    [string]$Python = "python",
    [string]$IssPath = "packaging/windows/SISTEMA_OPERA.iss"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

& $Python packaging/build.py --platform windows

$inno = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $inno) {
    Write-Warning "Inno Setup (iscc.exe) not found. Install Inno Setup and rerun to create the installer."
    exit 0
}

& $inno $IssPath
