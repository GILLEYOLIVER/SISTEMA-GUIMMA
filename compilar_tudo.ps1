# compilar_tudo.ps1
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "COMPILAR SISTEMA OPERA COMPLETO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# PASSO 1: Criar pastas necessárias
Write-Host "`n[1/5] Criando pastas..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "icons" -Force | Out-Null
New-Item -ItemType Directory -Path "dist\SistemaOpera" -Force | Out-Null

# PASSO 2: Verificar/Converter ícones
Write-Host "`n[2/5] Verificando ícones..." -ForegroundColor Yellow

# Verificar se o ícone do configurador existe
if (-not (Test-Path "icons\icon_config.png")) {
    Write-Host "Aviso: icon_config.png não encontrado em icons/" -ForegroundColor Yellow
    Write-Host "Copiando ICONE_SISTEMA.png como fallback..." -ForegroundColor Yellow
    if (Test-Path "icons\ICONE_SISTEMA.png") {
        Copy-Item "icons\ICONE_SISTEMA.png" "icons\icon_config.png" -Force
    }
}

# Converter PNG para ICO se necessário
if (Test-Path "icons\icon_config.png") {
    python -c "
from PIL import Image
img = Image.open('icons/icon_config.png')
img.save('icons/icon_config.ico', format='ICO', sizes=[(256,256), (128,128), (64,64), (32,32), (16,16)])
print('✅ icon_config.ico criado')
" 2>$null
}

if (Test-Path "icons\ICONE_SISTEMA.png") {
    python -c "
from PIL import Image
img = Image.open('icons/ICONE_SISTEMA.png')
img.save('icons/ICONE_SISTEMA.ico', format='ICO', sizes=[(256,256), (128,128), (64,64), (32,32), (16,16)])
print('✅ ICONE_SISTEMA.ico criado')
" 2>$null
}

# PASSO 3: Compilar configurador do banco
Write-Host "`n[3/5] Compilando configurador do banco..." -ForegroundColor Yellow
python packaging/windows/build_db_config.py

# PASSO 4: Compilar programa principal
Write-Host "`n[4/5] Compilando programa principal..." -ForegroundColor Yellow
python packaging/build.py --platform windows

# PASSO 5: Criar instalador com Inno Setup
Write-Host "`n[5/5] Criando instalador..." -ForegroundColor Yellow

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

if ($innoExe) {
    & $innoExe "packaging\windows\SISTEMA_OPERA_CORRIGIDO.iss"

    $installerPath = "dist\SistemaOpera_Setup.exe"
    if (Test-Path $installerPath) {
        $size = (Get-Item $installerPath).Length / 1MB
        Write-Host "`n========================================" -ForegroundColor Green
        Write-Host "✅ INSTALADOR CRIADO COM SUCESSO!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Arquivo: $installerPath"
        Write-Host "Tamanho: $([math]::Round($size, 2)) MB"
        Write-Host ""
        Write-Host "Conteúdo do instalador:"
        Write-Host "  - Programa principal: SistemaOpera.exe"
        Write-Host "  - Configurador: CONFIGURAR_BANCO.exe"
        Write-Host "  - Ícones: ICONE_SISTEMA.ico e icon_config.ico"

        $testar = Read-Host "`nTestar instalador agora? (s/n)"
        if ($testar -eq 's') {
            Start-Process $installerPath
        }
    }
} else {
    Write-Host "`n⚠️  Inno Setup não encontrado!" -ForegroundColor Yellow
    Write-Host "Os executáveis estão em: dist\SistemaOpera\" -ForegroundColor Yellow
}

Write-Host "`nProcesso concluído!" -ForegroundColor Green