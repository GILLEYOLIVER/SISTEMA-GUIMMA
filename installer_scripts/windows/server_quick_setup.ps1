Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
  [string]$PgSuperPassword = "admin",
  [string]$AppPassword = "opera123"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Compatível com dois layouts:
# 1) Instalador principal: {app}\tools\server_quick_setup.ps1
# 2) Instalador de banco dedicado: {app}\server_quick_setup.ps1
if (Test-Path (Join-Path $scriptDir "AUTO_SERVER_SETUP.exe")) {
  $toolsDir = $scriptDir
}
elseif (Test-Path (Join-Path $scriptDir "..\tools\AUTO_SERVER_SETUP.exe")) {
  $toolsDir = Resolve-Path (Join-Path $scriptDir "..\tools")
}
else {
  throw "Não consegui localizar AUTO_SERVER_SETUP.exe (nem em $scriptDir nem em ..\tools)."
}

$pgDir = Join-Path $toolsDir "postgresql"

Write-Host "[OPERA] Setup rápido do servidor iniciado..."

function Find-PostgresInstaller {
  param([string]$Root)

  if (-not (Test-Path $Root)) { return $null }

  $patterns = @(
    "postgresql-18*-windows-*.exe",
    "postgresql*-windows-*.exe",
    "*postgres*18*.exe",
    "*.exe"
  )

  foreach ($pattern in $patterns) {
    $candidate = Get-ChildItem -Path $Root -Filter $pattern -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) { return $candidate.FullName }
  }

  return $null
}

function Ensure-PostgresInstalled {
  $svc = Get-Service -Name "postgresql-x64-18" -ErrorAction SilentlyContinue
  if ($svc) {
    Write-Host "[OPERA] PostgreSQL 18 já instalado (serviço encontrado)."
    return
  }

  $installer = Find-PostgresInstaller -Root $pgDir
  if (-not $installer) {
    throw "Instalador do PostgreSQL não encontrado em: $pgDir"
  }

  Write-Host "[OPERA] Instalando PostgreSQL em modo silencioso..."
  $args = @(
    "--mode", "unattended",
    "--unattendedmodeui", "none",
    "--superpassword", $PgSuperPassword,
    "--servicename", "postgresql-x64-18",
    "--serverport", "5432"
  )

  $proc = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
  if ($proc.ExitCode -ne 0) {
    throw "Instalador PostgreSQL retornou código $($proc.ExitCode)."
  }

  Write-Host "[OPERA] PostgreSQL instalado com sucesso."
}

function Run-OperaServerConfig {
  $configPs1 = Join-Path $toolsDir "opera_server_config.ps1"
  if (-not (Test-Path $configPs1)) {
    throw "Arquivo não encontrado: $configPs1"
  }

  Write-Host "[OPERA] Aplicando configuração de rede/firewall do PostgreSQL..."
  & powershell -ExecutionPolicy Bypass -File $configPs1
  if ($LASTEXITCODE -ne 0) {
    throw "Falha ao executar opera_server_config.ps1"
  }
}

function Run-AutoServerSetup {
  $setupExe = Join-Path $toolsDir "AUTO_SERVER_SETUP.exe"
  if (-not (Test-Path $setupExe)) {
    throw "Arquivo não encontrado: $setupExe"
  }

  Write-Host "[OPERA] Criando banco/schema e gerando server_info.json..."
  $env:OPERA_PG_SUPERPASS = $PgSuperPassword
  $env:OPERA_PG_APP_PASS = $AppPassword

  $proc = Start-Process -FilePath $setupExe -Wait -PassThru
  if ($proc.ExitCode -ne 0) {
    throw "AUTO_SERVER_SETUP.exe retornou código $($proc.ExitCode)."
  }
}

try {
  Ensure-PostgresInstalled
  Run-OperaServerConfig
  Run-AutoServerSetup

  Write-Host ""
  Write-Host "[OPERA] Setup do servidor concluído com sucesso." -ForegroundColor Green
  Write-Host "Arquivo de conexão salvo em C:\ProgramData\Opera\server_info.json" -ForegroundColor Green
}
catch {
  Write-Error "[OPERA] Falha no setup do servidor: $($_.Exception.Message)"
  exit 1
}

exit 0
