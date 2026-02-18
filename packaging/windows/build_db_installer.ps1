# packaging/windows/build_db_installer.ps1
param(
    [string]$Python = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  OPERA - CONSTRUTOR DO INSTALADOR DE BANCO" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

function Run-Step([string]$title, [scriptblock]$action) {
    Write-Host ""
    Write-Host $title -ForegroundColor Green
    & $action
}

Run-Step "[1/4] Preparando icone..." {
    & $Python "packaging/windows/prepare_icon.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao preparar icone." }
}

Run-Step "[2/4] Construindo configurador do banco..." {
    & $Python "packaging/windows/build_db_config.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do configurador." }
}

Run-Step "[3/4] Construindo setup automático do servidor..." {
    & $Python "packaging/windows/build_server_setup.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do AUTO_SERVER_SETUP." }
}

Run-Step "[4/4] Criando instalador de banco..." {
    $innoPaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )

    $innoExe = $null
    foreach ($p in $innoPaths) {
        if ($p -and (Test-Path $p)) { $innoExe = $p; break }
    }

    if (-not $innoExe) {
        throw "Inno Setup nao encontrado. Instale o Inno Setup 6."
    }

    $issPath = Join-Path $repoRoot "packaging\windows\BANCO_OPERA.iss"
    if (-not (Test-Path $issPath)) {
        throw "Arquivo .iss nao encontrado: $issPath"
    }

    $outPath = Join-Path $repoRoot "dist\BancoDadosOpera_Setup.exe"
    Remove-Item $outPath -ErrorAction SilentlyContinue

    & $innoExe $issPath
    if ($LASTEXITCODE -ne 0) {
        throw "ISCC falhou ao criar instalador do banco."
    }

    if (-not (Test-Path $outPath)) {
        throw "Instalador não gerado: $outPath"
    }

    Write-Host "OK instalador banco: $outPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "Processo concluido!" -ForegroundColor Green
