# build_configurador_postgres.ps1
# Compila o configurar_postgres.py e inclui a pasta scripts/ no dist
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\build_configurador_postgres.ps1
# Ou clique direito -> Executar com PowerShell

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Ok($m){ Write-Host "[OK]   $m" -ForegroundColor Green }
function Fail($m){ Write-Host "[ERRO] $m" -ForegroundColor Red }

$root = (Resolve-Path $PSScriptRoot).Path
Set-Location $root

$pyFile = Join-Path $root "configurar_postgres.py"
if (!(Test-Path $pyFile)) { throw "Não encontrei configurar_postgres.py na raiz: $pyFile" }

$scriptsDir = Join-Path $root "scripts"
if (!(Test-Path $scriptsDir)) { throw "Não encontrei a pasta scripts na raiz: $scriptsDir" }

# Python preferencial: .venv\Scripts\python.exe
$python = Join-Path $root ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
  $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (!$python -or !(Test-Path $python)) { throw "Python não encontrado. Use .venv ou instale Python." }

Info "Python: $python"
Info "Projeto: $root"
Info "Scripts: $scriptsDir"

Info "Instalando dependências de build..."
& $python -m pip install --upgrade pip | Out-Null
& $python -m pip install --upgrade pyinstaller customtkinter | Out-Null
Ok "Deps OK"

$appName = "OPERA_CONFIG_POSTGRES"
$distDir = Join-Path $root "dist"
$buildDir = Join-Path $root "build"

if (Test-Path $distDir) { Remove-Item $distDir -Recurse -Force }
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }

# ONEDIR (RECOMENDADO): gera pasta com exe + scripts
Info "Compilando (ONEDIR) com PyInstaller e embutindo scripts..."
& $python -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --windowed `
  --name $appName `
  --add-data ("scripts" + [IO.Path]::PathSeparator + "scripts") `
  $pyFile

Ok "Build concluído!"

$targetAppDir = Join-Path $distDir $appName
$targetScripts = Join-Path $targetAppDir "scripts"

# Garantia extra: copia scripts se por algum motivo não estiver lá
if (!(Test-Path $targetScripts)) {
  Info "Copiando scripts para o dist (garantia)..."
  Copy-Item $scriptsDir $targetScripts -Recurse -Force
}

$exe = Join-Path $targetAppDir ($appName + ".exe")
if (Test-Path $exe) {
  Ok "EXE gerado em: $exe"
  Ok "Pasta scripts em: $targetScripts"
} else {
  Fail "Não encontrei o exe esperado: $exe"
}

Info "IMPORTANTE: envie a pasta inteira:"
Info "  dist\$appName\"
Info "Não envie apenas o .exe, pois a pasta scripts deve ir junto."
