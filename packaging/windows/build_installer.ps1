# packaging/windows/build_installer_completo.ps1

param(
    [string]$Python = "python",
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "  SISTEMA OPERA - CONSTRUTOR DE INSTALADOR" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# PASSO 1: Preparar ícone
Write-Host "`n[1/4] Preparando ícone..." -ForegroundColor Green
& $Python packaging/windows/prepare_icon.py

# PASSO 2: Construir app principal
Write-Host "`n[2/4] Construindo aplicativo principal..." -ForegroundColor Green
& $Python packaging/build.py --platform windows

# PASSO 3: Construir configurador do banco
Write-Host "`n[3/4] Construindo configurador do banco..." -ForegroundColor Green
& $Python packaging/windows/build_db_config.py

# PASSO 4: Criar instalador
Write-Host "`n[4/4] Criando instalador..." -ForegroundColor Green

# Encontrar Inno Setup
$innoPaths = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

$innoExe = $null
foreach ($path in $innoPaths) {
    if (Test-Path $path) {
        $innoExe = $path
        break
    }
}

if (-not $innoExe) {
    Write-Host "❌ Inno Setup não encontrado!" -ForegroundColor Red
    Write-Host "Por favor, instale o Inno Setup 6: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Inno Setup encontrado: $innoExe" -ForegroundColor Green

# Compilar instalador
& $innoExe "packaging\windows\SISTEMA_OPERA_CORRIGIDO.iss"

# Verificar resultado
$installerPath = "dist\SistemaOpera_Setup.exe"
if (Test-Path $installerPath) {
    $installerSize = (Get-Item $installerPath).Length / 1MB
    Write-Host "`n✅ INSTALADOR CRIADO COM SUCESSO!" -ForegroundColor Green
    Write-Host "📦 Arquivo: $installerPath" -ForegroundColor Green
    Write-Host "📏 Tamanho: $([math]::Round($installerSize, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "❌ Instalador não foi criado!" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Processo concluído!" -ForegroundColor Green