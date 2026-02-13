# packaging/windows/fazer_instalador.ps1
# Script simples para criar o instalador

Write-Host "========================================================"
Write-Host "CRIAR INSTALADOR DO SISTEMA OPERA"
Write-Host "========================================================"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

# PASSO 1: Verificar se os executáveis existem
Write-Host ""
Write-Host "[1/3] Verificando arquivos necessários..." -ForegroundColor Cyan

$arquivos_ok = $true

if (Test-Path "dist\SistemaOpera\SistemaOpera.exe") {
    $tamanho = (Get-Item "dist\SistemaOpera\SistemaOpera.exe").Length / 1MB
    Write-Host "  ✅ SistemaOpera.exe encontrado ($([math]::Round($tamanho,2)) MB)" -ForegroundColor Green
} else {
    Write-Host "  ❌ SistemaOpera.exe NÃO encontrado!" -ForegroundColor Red
    Write-Host "     Execute primeiro: python packaging/build.py --platform windows"
    $arquivos_ok = $false
}

if (Test-Path "dist\SistemaOpera\CONFIGURAR_BANCO.exe") {
    $tamanho = (Get-Item "dist\SistemaOpera\CONFIGURAR_BANCO.exe").Length / 1MB
    Write-Host "  ✅ CONFIGURAR_BANCO.exe encontrado ($([math]::Round($tamanho,2)) MB)" -ForegroundColor Green
} else {
    Write-Host "  ❌ CONFIGURAR_BANCO.exe NÃO encontrado!" -ForegroundColor Red
    Write-Host "     Execute primeiro: python packaging/windows/build_db_config.py"
    $arquivos_ok = $false
}

if (Test-Path "icons\ICONE_SISTEMA.ico") {
    Write-Host "  ✅ ICONE_SISTEMA.ico encontrado" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  ICONE_SISTEMA.ico não encontrado, mas será criado..." -ForegroundColor Yellow
    python packaging/windows/prepare_icon.py
}

if (-not $arquivos_ok) {
    Write-Host ""
    Write-Host "ERRO: Arquivos necessários não encontrados!" -ForegroundColor Red
    exit 1
}

# PASSO 2: Encontrar Inno Setup
Write-Host ""
Write-Host "[2/3] Procurando Inno Setup..." -ForegroundColor Cyan

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
    Write-Host "  ❌ Inno Setup não encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Para testar o configurador manualmente:" -ForegroundColor Yellow
    Write-Host "  .\dist\SistemaOpera\CONFIGURAR_BANCO.exe" -ForegroundColor White
    exit 1
}

Write-Host "  ✅ Inno Setup encontrado: $innoExe" -ForegroundColor Green

# PASSO 3: Compilar instalador
Write-Host ""
Write-Host "[3/3] Compilando instalador..." -ForegroundColor Cyan

& $innoExe "packaging\windows\instalador_final.iss"

# Verificar resultado
$installerPath = "dist\SistemaOpera_Setup.exe"
if (Test-Path $installerPath) {
    $tamanho = (Get-Item $installerPath).Length / 1MB
    Write-Host ""
    Write-Host "========================================================"
    Write-Host "✅ INSTALADOR CRIADO COM SUCESSO!" -ForegroundColor Green
    Write-Host "========================================================"
    Write-Host "Arquivo: $installerPath"
    Write-Host "Tamanho: $([math]::Round($tamanho,2)) MB"
    Write-Host ""
    Write-Host "Conteúdo do instalador:"
    Write-Host "  - Aplicativo: SistemaOpera.exe"
    Write-Host "  - Configurador: CONFIGURAR_BANCO.exe"
    Write-Host "  - Ícone: ICONE_SISTEMA.ico"
    Write-Host ""

    $testar = Read-Host "Testar instalador agora? (s/n)"
    if ($testar -eq 's') {
        Start-Process $installerPath
    }
} else {
    Write-Host ""
    Write-Host "❌ ERRO: Instalador não foi criado!" -ForegroundColor Red
}