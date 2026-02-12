# packaging/windows/build_installer.ps1 (VERSÃO CORRIGIDA)
<#
.SYNOPSIS
    Script para construir o instalador completo do Sistema Opera - VERSÃO CORRIGIDA
#>

param(
    [Alias("SkipAppBuild")][switch]$SkipBuild,
    [switch]$SkipIcon,
    [switch]$SkipInstaller,
    [switch]$Clean,
    [string]$InnoPath = "",
    [string]$Python = "python",
    [string]$Version = ""
)

# Configuração
$ErrorActionPreference = "Stop"

# Função para imprimir cabeçalho
function Write-Header {
    param([string]$Title)
    Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-Success { param([string]$Message) Write-Host "$Message" -ForegroundColor Green }
function Write-Error { param([string]$Message) Write-Host "$Message" -ForegroundColor Red }
function Write-Warning { param([string]$Message) Write-Host "WARNING: $Message" -ForegroundColor Yellow }
function Write-Info { param([string]$Message) Write-Host "INFO: $Message" -ForegroundColor Blue }

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.Path]::GetFullPath((Join-Path $PWD $Path))
}

function Test-SameFilePath {
    param(
        [Parameter(Mandatory = $true)][string]$FirstPath,
        [Parameter(Mandatory = $true)][string]$SecondPath
    )

    $firstFullPath = Resolve-FullPath $FirstPath
    $secondFullPath = Resolve-FullPath $SecondPath

    if (Test-Path $firstFullPath) {
        $firstFullPath = (Get-Item $firstFullPath).FullName
    }

    if (Test-Path $secondFullPath) {
        $secondFullPath = (Get-Item $secondFullPath).FullName
    }

    return $firstFullPath.TrimEnd('\').ToLowerInvariant() -eq $secondFullPath.TrimEnd('\').ToLowerInvariant()
}

# INÍCIO DO SCRIPT
Write-Header "SISTEMA OPERA - CONSTRUCAO DE INSTALADOR (CORRIGIDO)"
Write-Info "Diretório: $PWD"

if (-not [string]::IsNullOrWhiteSpace($Version)) {
    Write-Info "Versao alvo: $Version"
}

# PASSO 1: PREPARAR ICONE
if (-not $SkipIcon) {
    Write-Header "PASSO 1: PREPARANDO ICONE"
    
    $iconScript = "packaging\windows\prepare_icon.py"
    
    if (Test-Path $iconScript) {
        Write-Info "Convertendo icone PNG para ICO..."
        
        try {
            & $Python $iconScript
            Write-Success "Conversão do icone concluída"
        } catch {
            Write-Warning "Falha ao converter icone: $_"
        }
    } else {
        Write-Error "Script de icone não encontrado"
        exit 1
    }
}

# PASSO 2: CONSTRUIR EXECUTAVEL
if (-not $SkipBuild) {
    Write-Header "PASSO 2: CONSTRUINDO EXECUTAVEL"
    
    $buildScript = "packaging\build.py"
    
    if (Test-Path $buildScript) {
        Write-Info "Executando build do PyInstaller..."
        
        try {
            # Limpar builds anteriores
            if (Test-Path "dist") {
                Remove-Item "dist" -Recurse -Force -ErrorAction SilentlyContinue
            }
            if (Test-Path "build") {
                Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue
            }
            
            # Executar build
            & $Python $buildScript --platform windows
            
            # Verificar se executável foi criado
            $exePaths = @(
                "dist\windows\SistemaOpera.exe",
                "dist\SistemaOpera.exe",
                "dist\SistemaOpera\SistemaOpera.exe"
            )
            
            $exeFound = $false
            foreach ($path in $exePaths) {
                if (Test-Path $path) {
                    $exeSize = (Get-Item $path).Length / 1MB
                    Write-Success ("Executavel encontrado: {0} ({1} MB)" -f $path, [math]::Round($exeSize, 2))
                    $exeFound = $true
                    
                    # Criar pasta para instalador
                    $targetDir = "dist\SistemaOpera"
                    if (-not (Test-Path $targetDir)) {
                        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                    }
                    
                    # Copiar executável (evita copiar sobre ele mesmo)
                    $destinationExe = Join-Path $targetDir "SistemaOpera.exe"

                    if (-not (Test-SameFilePath -FirstPath $path -SecondPath $destinationExe)) {
                        Copy-Item $path -Destination $destinationExe -Force
                    } else {
                        Write-Info "Executavel ja esta no destino esperado: $destinationExe"
                    }
                    
                    # Copiar icone
                    $iconPath = "icons\ICONE_SISTEMA.ico"
                    if (Test-Path $iconPath) {
                        Copy-Item $iconPath -Destination "$targetDir\ICONE_SISTEMA.ico" -Force
                        Write-Success "Ícone copiado"
                    }
                    
                    # Copiar dados se existirem
                    if (Test-Path "data") {
                        Copy-Item "data\*" -Destination "$targetDir\data\" -Recurse -Force -ErrorAction SilentlyContinue
                    }
                    
                    break
                }
            }
            
            if (-not $exeFound) {
                Write-Error "Nenhum executável foi criado"
                Write-Info "Verifique os logs do PyInstaller acima"
                exit 1
            }
            
        } catch {
            Write-Error "Falha no build: $_"
            exit 1
        }
    } else {
        Write-Error "Script de build não encontrado"
        exit 1
    }
}

# PASSO 3: VERIFICAR ARQUIVOS
Write-Header "PASSO 3: VERIFICANDO ARQUIVOS"
$requiredFiles = @(
    "dist\SistemaOpera\SistemaOpera.exe"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length / 1KB
        Write-Success ("{0} ({1} KB)" -f $file, [math]::Round($size, 2))
    } else {
        Write-Error "$file (NAO ENCONTRADO)"
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Error "Arquivos faltando. O build pode ter falhado."
    exit 1
}

# PASSO 4: CRIAR INSTALADOR COM INNO SETUP
if (-not $SkipInstaller) {
    Write-Header "PASSO 4: CRIANDO INSTALADOR COM INNO SETUP"
    
    # Verificar se Inno Path foi fornecido
    if ($InnoPath -ne "") {
        $innoExe = $InnoPath
    } else {
        # Encontrar Inno Setup automaticamente
        $innoPaths = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            "C:\Program Files\Inno Setup 6\ISCC.exe",
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
        )
        
        $innoExe = $null
        foreach ($path in $innoPaths) {
            if (Test-Path $path) {
                $innoExe = $path
                break
            }
        }
    }
    
    if (-not $innoExe) {
        Write-Error "Inno Setup não encontrado!"
        Write-Info ""
        Write-Info "SOLUÇÕES:"
        Write-Info "   1. Instale o Inno Setup: https://jrsoftware.org/isdl.php"
        Write-Info "   2. Ou execute manualmente depois de instalar:"
        Write-Info "      ISCC.exe packaging\windows\SISTEMA_OPERA.iss"
        Write-Info "   3. Ou especifique o caminho: -InnoPath 'C:\Program Files\...\ISCC.exe'"
        Write-Info ""
        
        $installChoice = Read-Host "Deseja instalar o Inno Setup agora? (s/n)"
        if ($installChoice -match '^[sSyY]') {
            Write-Info "Baixando Inno Setup..."
            $url = "https://jrsoftware.org/download.php/is.exe"
            $setupPath = "$env:TEMP\InnoSetup.exe"
            
            try {
                Invoke-WebRequest -Uri $url -OutFile $setupPath
                Write-Info "Instalando Inno Setup..."
                Start-Process -FilePath $setupPath -Wait
                Write-Success "Inno Setup instalado. Reinicie o script."
            } catch {
                Write-Error "Falha ao baixar/instalar: $_"
            }
        }
        
        exit 1
    }
    
    Write-Info "Inno Setup encontrado: $innoExe"
    
    # Verificar script ISS
    $issScript = "packaging\windows\SISTEMA_OPERA.iss"
    if (-not (Test-Path $issScript)) {
        Write-Error "Script ISS não encontrado: $issScript"
        exit 1
    }
    
    # Compilar instalador
    Write-Info "Compilando instalador..."
    try {
        & $innoExe $issScript
        
        # Verificar se instalador foi criado
        $installerPaths = @(
            "dist\SistemaOpera_Setup.exe",
            "Output\SistemaOpera_Setup.exe"
        )
        
        $installerCreated = $false
        foreach ($path in $installerPaths) {
            if (Test-Path $path) {
                $installerSize = (Get-Item $path).Length / 1MB
                Write-Success "INSTALADOR CRIADO COM SUCESSO!"
                Write-Host ""
                Write-Host "Arquivo: $path" -ForegroundColor Green
                Write-Host ("Tamanho: {0} MB" -f [math]::Round($installerSize, 2)) -ForegroundColor Green
                Write-Host ""
                $installerCreated = $true
                
                # Mover para dist se não estiver lá
                if ($path -ne "dist\SistemaOpera_Setup.exe") {
                    Move-Item $path -Destination "dist\SistemaOpera_Setup.exe" -Force
                    Write-Info "Instalador movido para: dist\SistemaOpera_Setup.exe"
                }
                
                break
            }
        }
        
        if (-not $installerCreated) {
            Write-Error "Instalador não foi criado"
            Write-Info "Tente compilar manualmente:"
            Write-Info "   '$innoExe' '$issScript'"
            exit 1
        }
        
    } catch {
        Write-Error "Falha ao compilar instalador: $_"
        exit 1
    }
}

# FIM
Write-Header "PROCESSO CONCLUIDO"
Write-Success "Todas as etapas foram concluidas!"

if (Test-Path "dist\SistemaOpera_Setup.exe") {
    Write-Host ""
    Write-Host "INSTALADOR PRONTO: dist\SistemaOpera_Setup.exe" -ForegroundColor Green
    Write-Host ""
    Write-Host "Para testar:" -ForegroundColor Cyan
    Write-Host "   1. Execute: dist\SistemaOpera_Setup.exe" -ForegroundColor Gray
    Write-Host "   2. Configure o banco de dados no assistente" -ForegroundColor Gray
    Write-Host "   3. Verifique se o icone aparece" -ForegroundColor Gray
    Write-Host ""
    
    # Abrir pasta
    $openFolder = Read-Host "Abrir pasta do instalador? (s/n)"
    if ($openFolder -match '^[sSyY]') {
        explorer "dist"
    }
} else {
    Write-Info "Conteudo criado em: dist\"
    Get-ChildItem "dist\" -Recurse | ForEach-Object {
        Write-Host "  - $($_.FullName.Replace($PWD + '\', ''))" -ForegroundColor Gray
    }
}
