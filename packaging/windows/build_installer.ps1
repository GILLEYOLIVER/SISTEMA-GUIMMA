# packaging/windows/build_installer.ps1
# ASCII-only where possible; output in UTF-8; stop on errors.

param(
    [string]$Python = "python",
    [string]$Version = "1.1.1",
    [ValidateSet("x64", "x86")]
    [string]$Architecture = "x64"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Force UTF-8 output
try { chcp 65001 | Out-Null } catch { }
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path
Set-Location $repoRoot


function Get-PythonArch([string]$PyCmd) {
    $arch = & $PyCmd -c "import struct; print('x64' if struct.calcsize('P')*8==64 else 'x86')"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($arch)) {
        throw "Failed to detect Python architecture from '$PyCmd'."
    }
    return $arch.Trim()
}


Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  SISTEMA GUIMMA - CONSTRUTOR DE INSTALADOR" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

$pythonArch = Get-PythonArch $Python
Write-Host "Python architecture detected: $pythonArch" -ForegroundColor Cyan
if ($pythonArch -ne $Architecture) {
    throw "Requested architecture '$Architecture' but Python is '$pythonArch'. Use a matching Python interpreter."
}


function Run-Step([string]$title, [scriptblock]$action) {
    Write-Host ""
    Write-Host $title -ForegroundColor Green
    & $action
}

function Show-LastLines([string]$path, [int]$lines = 80) {
    if (Test-Path $path) {
        Write-Host "" 
        Write-Host "---- ULTIMAS LINHAS: $path ----" -ForegroundColor Yellow
        try {
            Get-Content -LiteralPath $path -Tail $lines | ForEach-Object { $_ }
        } catch {
            Write-Host "(nao foi possivel ler o log)" -ForegroundColor Yellow
        }
        Write-Host "---- FIM ----" -ForegroundColor Yellow
        Write-Host ""
    }
}

# PASSO 1: Preparar icone
Run-Step "[1/4] Preparando icone..." {
    & $Python "packaging/windows/prepare_icon.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao preparar icone." }
}

# PASSO 2: Construir app principal
Run-Step "[2/4] Construindo aplicativo principal..." {
    & $Python "packaging/build.py" --platform windows
    if ($LASTEXITCODE -ne 0) {
        # Mostra log do build.py (quando existir)
        Show-LastLines (Join-Path $repoRoot "build\pyinstaller_windows_error.log") 120
        throw "Falha no build do app principal."
    }
}

# PASSO 3: Construir configurador do banco
Run-Step "[3/4] Construindo configurador do banco..." {
    & $Python "packaging/windows/build_db_config.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do configurador do banco." }
}

# PASSO 3.2: Construir app de licenciamento
Run-Step "[3.2/5] Construindo app de licenciamento..." {
    & $Python -m PyInstaller --clean --noconfirm "SistemaGuimmaLicenca.spec"
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do app de licenciamento." }

    $licenseExe = Join-Path $repoRoot "dist\SistemaGuimmaLicenca.exe"
    if (-not (Test-Path $licenseExe)) {
        throw "Executavel de licenciamento nao encontrado: $licenseExe"
    }
}

# PASSO 3.3: Construir configurador PostgreSQL
Run-Step "[3.3/5] Construindo configurador PostgreSQL..." {
    $pgIconCandidates = @(
        (Join-Path $repoRoot "icons\PG_ICON.ico"),
        (Join-Path $repoRoot "PG_ICON.ico")
    )
    $pgIcon = $null
    foreach ($candidate in $pgIconCandidates) {
        if (Test-Path $candidate) {
            $pgIcon = $candidate
            break
        }
    }

    if (-not $pgIcon) {
        throw "Icone PG_ICON.ico nao encontrado em icons\PG_ICON.ico."
    }

    $configPostgresScript = Join-Path $repoRoot "configurar_postgres.py"
    if (-not (Test-Path $configPostgresScript)) {
        throw "Arquivo nao encontrado: $configPostgresScript"
    }

    $scriptsDir = Join-Path $repoRoot "SCRIPTS"
    if (-not (Test-Path $scriptsDir)) {
        throw "Pasta SCRIPTS nao encontrada."
    }

    $configPostgresOut = Join-Path $repoRoot "dist\SistemaGuimma"
    New-Item -ItemType Directory -Force -Path $configPostgresOut | Out-Null

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name "CONFIGURAR_POSTGRES" `
        --icon "$pgIcon" `
        --distpath "$configPostgresOut" `
        --workpath (Join-Path $repoRoot "build\pyi_configurar_postgres") `
        --specpath (Join-Path $repoRoot "build") `
        --add-data "$scriptsDir;SCRIPTS" `
        --hidden-import "tkinter" `
        --hidden-import "customtkinter" `
        --hidden-import "winreg" `
        --hidden-import "ctypes" `
        "$configPostgresScript"

    if ($LASTEXITCODE -ne 0) { throw "Falha no build do configurador PostgreSQL." }

    $configPostgresExe = Join-Path $configPostgresOut "CONFIGURAR_POSTGRES.exe"
    if (-not (Test-Path $configPostgresExe)) {
        throw "CONFIGURAR_POSTGRES.exe nao encontrado: $configPostgresExe"
    }
}

# PASSO 3.5: Verificacao rapida (runtime do PyInstaller)
Run-Step "[3.5/5] Verificando runtime (_internal\\python312.dll)..." {
    $candidates = @(
        (Join-Path $repoRoot "dist\SistemaGuimma\_internal\python312.dll"),
        (Join-Path $repoRoot "dist\windows\SistemaGuimma\_internal\python312.dll"),
        (Join-Path $repoRoot "dist\windows\_internal\python312.dll")
    )

    $found = $false
    foreach ($p in $candidates) {
        if (Test-Path $p) { $found = $true; Write-Host "OK runtime encontrado: $p" -ForegroundColor Green; break }
    }

    if (-not $found) {
        throw "Build incompleto: python312.dll nao encontrado. O instalador precisa da pasta _internal junto do exe." 
    }
}

# PASSO 4: Criar instalador
Run-Step "[4/5] Criando instalador..." {

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

    $issPath = Join-Path $repoRoot "packaging\windows\SISTEMA_GUIMMA.iss"
    if (-not (Test-Path $issPath)) {
        throw "Arquivo .iss nao encontrado: $issPath"
    }

    # Garantir que o .iss esteja em UTF-8 sem BOM
    $bytes = [System.IO.File]::ReadAllBytes($issPath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $bytes = $bytes[3..($bytes.Length-1)]
        [System.IO.File]::WriteAllBytes($issPath, $bytes)
    }

    # Apagar instalador antigo
    $installerPath = Join-Path $repoRoot ("dist\Sistema_Guimma_Setup_" + $Architecture + ".exe")
    Remove-Item $installerPath -ErrorAction SilentlyContinue

    & $innoExe "/DARCH=$Architecture" "/DAPP_VERSION=`"$Version`"" $issPath
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
    Write-Host "Arquitetura: $Architecture" -ForegroundColor Green
    Write-Host ("Tamanho: {0:N2} MB" -f $installerSize) -ForegroundColor Green
}

Write-Host ""
Write-Host "Processo concluido!" -ForegroundColor Green
