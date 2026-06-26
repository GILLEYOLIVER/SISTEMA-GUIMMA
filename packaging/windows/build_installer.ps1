# packaging/windows/build_installer.ps1
# ASCII-only where possible; output in UTF-8; stop on errors.

param(
    [string]$Python = "python",
    [string]$Version = "1.0.0",
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

# PASSO 3.5: Verificacao rapida (runtime do PyInstaller)
Run-Step "[3.5/4] Verificando runtime (_internal\\python312.dll)..." {
    $candidates = @(
        (Join-Path $repoRoot "dist\SistemaOpera\_internal\python312.dll"),
        (Join-Path $repoRoot "dist\windows\SistemaOpera\_internal\python312.dll"),
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
Run-Step "[4/4] Criando instalador..." {

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

    # Garantir que o .iss esteja em UTF-8 sem BOM
    $bytes = [System.IO.File]::ReadAllBytes($issPath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $bytes = $bytes[3..($bytes.Length-1)]
        [System.IO.File]::WriteAllBytes($issPath, $bytes)
    }

    # Apagar instalador antigo
    $installerPath = Join-Path $repoRoot ("dist\SistemaOpera_Setup_" + $Architecture + ".exe")
    Remove-Item $installerPath -ErrorAction SilentlyContinue

    & $innoExe "/DARCH=$Architecture" $issPath
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
