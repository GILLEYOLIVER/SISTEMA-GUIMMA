# opera_server_config.ps1
# Configura PostgreSQL 18 para aceitar conexao local + rede, abre firewall e reinicia servico.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-Pg18ServiceName {
  $svc = Get-Service -Name "postgresql-x64-18" -ErrorAction SilentlyContinue
  if ($svc) { return $svc.Name }
  $svc2 = Get-Service | Where-Object { $_.Name -match "postgres" -and $_.Name -match "18" } | Select-Object -First 1
  if ($svc2) { return $svc2.Name }
  throw "Nao encontrei o servico do PostgreSQL 18."
}

function Get-DataDirFromService([string]$serviceName) {
  $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$serviceName"
  $imagePath = (Get-ItemProperty -Path $regPath -Name ImagePath).ImagePath
  $m = [regex]::Match($imagePath, "-D\s+`"([^`"]+)`"")
  if ($m.Success) { return $m.Groups[1].Value }
  $m2 = [regex]::Match($imagePath, "-D\s+([^\s]+)")
  if ($m2.Success) { return $m2.Groups[1].Value }
  throw "Nao consegui obter DataDir do serviço."
}

function Get-LocalNetworks {
  $ipList = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.PrefixLength -ge 8 -and $_.PrefixLength -le 30 }

  $upIf = @(
    Get-NetAdapter -ErrorAction SilentlyContinue |
      Where-Object { $_.Status -eq "Up" } |
      Select-Object -ExpandProperty ifIndex
  )

  if ($upIf.Count -gt 0) {
    $ipList = $ipList | Where-Object { $upIf -contains $_.InterfaceIndex }
  }

  function ToU32($ip) {
    $b=[System.Net.IPAddress]::Parse($ip).GetAddressBytes(); [Array]::Reverse($b); [BitConverter]::ToUInt32($b,0)
  }
  function FromU32([uint32]$u) {
    $b=[BitConverter]::GetBytes($u); [Array]::Reverse($b); ([System.Net.IPAddress]::new($b)).ToString()
  }

  $nets = @()
  foreach ($a in $ipList) {
    $ipU = ToU32 $a.IPAddress
    $maskU = ([uint32]0xFFFFFFFF) -shl (32 - $a.PrefixLength)
    $netU = $ipU -band $maskU
    $nets += ("{0}/{1}" -f (FromU32 $netU), $a.PrefixLength)
  }
  $nets | Select-Object -Unique
}

function Ensure-LineReplace([string]$path, [string]$pattern, [string]$replacement) {
  $lines = Get-Content $path -Encoding UTF8
  $found = $false
  for ($i=0; $i -lt $lines.Count; $i++){
    if ($lines[$i] -match $pattern) { $lines[$i] = $replacement; $found=$true; break }
  }
  if (-not $found) { $lines += ""; $lines += $replacement }
  Set-Content -Path $path -Value $lines -Encoding UTF8
}

function Ensure-PgHba([string]$hbaPath, [string[]]$nets) {
  $lines = Get-Content $hbaPath -Encoding UTF8
  $tag = "# --- OPERA AUTO ---"
  if (-not ($lines -contains $tag)) { $lines += ""; $lines += $tag }
  foreach($n in $nets){
    $rule = "host    all             all             $n            scram-sha-256"
    $exists = $false
    foreach($l in $lines){
      if (($l -replace '\s+',' ').Trim().ToLower() -eq ($rule -replace '\s+',' ').Trim().ToLower()) { $exists=$true; break }
    }
    if (-not $exists){ $lines += $rule }
  }
  Set-Content -Path $hbaPath -Value $lines -Encoding UTF8
}

$svc = Get-Pg18ServiceName
$dataDir = Get-DataDirFromService $svc
$conf = Join-Path $dataDir "postgresql.conf"
$hba  = Join-Path $dataDir "pg_hba.conf"

# listen_addresses = '*'
Ensure-LineReplace $conf '^\s*#?\s*listen_addresses\s*=' "listen_addresses = '*'"

# libera redes detectadas (ex: 192.168.0.0/24)
$nets = Get-LocalNetworks
if (-not $nets -or $nets.Count -eq 0) { $nets = @("192.168.0.0/24") } # fallback
Ensure-PgHba $hba $nets

# firewall Any profile (pra não depender de Private/Public)
New-NetFirewallRule -DisplayName "PostgreSQL 18 (OPERA) - TCP 5432 (Any)" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5432 -Profile Any -ErrorAction SilentlyContinue | Out-Null

Restart-Service $svc -Force
Start-Sleep -Seconds 2

Write-Host "OK. Servico: $svc | DataDir: $dataDir | Redes: $($nets -join ', ')"
netstat -ano | findstr ":5432"
