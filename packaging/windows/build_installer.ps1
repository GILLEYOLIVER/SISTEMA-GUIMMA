# packaging/windows/build_installer.ps1
# ASCII-only where possible; output in UTF-8; stop on errors.

param(
    [string]$Python = "python",
    [string]$Version = "1.0.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Force UTF-8 output (helps avoid "Ã­" / "âœ…" on some terminals)
try {
    chcp 65001 | Out-Null
} catch { }
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
} catch { }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  SISTEMA OPERA - CONSTRUTOR DE INSTALADOR" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

function Run-Step([string]$title, [scriptblock]$action) {
    Write-Host ""
    Write-Host $title -ForegroundColor Green
    & $action
}

# PASSO 1: Preparar ícone
Run-Step "[1/5] Preparando icone..." {
    & $Python "packaging/windows/prepare_icon.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao preparar icone." }
}

# PASSO 2: Construir app principal
Run-Step "[2/5] Construindo aplicativo principal..." {
    & $Python "packaging/build.py" --platform windows
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do app principal." }
}

# PASSO 3: Construir configurador do banco
Run-Step "[3/5] Construindo configurador do banco..." {
    & $Python "packaging/windows/build_db_config.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do configurador do banco." }
}

# PASSO 4: Construir setup automático de servidor
Run-Step "[4/5] Construindo setup automático de servidor..." {
    & $Python "packaging/windows/build_server_setup.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do setup automático de servidor." }
}

# PASSO 5: Criar instalador
Run-Step "[5/5] Criando instalador..." {

    # Encontrar Inno Setup (ISCC)
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

    Write-Host "OK Inno Setup: $innoExe" -ForegroundColor Green

    $issPath = Join-Path $repoRoot "packaging\windows\SISTEMA_OPERA.iss"
    if (-not (Test-Path $issPath)) {
        throw "Arquivo .iss nao encontrado: $issPath"
    }

    # Garantir que o .iss esteja em UTF-8 sem BOM (evita 'Text is not inside a section')
    $bytes = [System.IO.File]::ReadAllBytes($issPath)
    # Remove BOM se existir (EF BB BF)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $bytes = $bytes[3..($bytes.Length-1)]
        [System.IO.File]::WriteAllBytes($issPath, $bytes)
    }

    # Apagar instalador antigo para nao dar "sucesso falso"
    $installerPath = Join-Path $repoRoot "dist\SistemaOpera_Setup.exe"
    Remove-Item $installerPath -ErrorAction SilentlyContinue

    # Compilar
    & $innoExe $issPath
    if ($LASTEXITCODE -ne 0) {
        throw "ISCC falhou. Veja a mensagem acima (arquivo faltando / caminho errado)."
    }

    if (-not (Test-Path $installerPath)) {
        throw "ISCC terminou sem gerar o instalador: $installerPath"
    }

    $installerSize = (Get-Item $installerPath).Length / 1MB
    Write-Host ""
    Write-Host "INSTALADOR CRIADO COM SUCESSO!" -ForegroundColor Green
    Write-Host "Arquivo: $installerPath" -ForegroundColor Green
    Write-Host ("Tamanho: {0:N2} MB" -f $installerSize) -ForegroundColor Green
}

Write-Host ""
Write-Host "Processo concluido!" -ForegroundColor Green
