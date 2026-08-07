param([string]$Name = "")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backupDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($Name)) { $Name = "fc26-$stamp" }
$safeName = ($Name -replace '[^a-zA-Z0-9_-]', '_')
$dbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "fc26" }
$dbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "fc26" }
Push-Location $root
try {
  docker compose exec -T database pg_dump -U $dbUser -d $dbName -Fc -f "/backups/$safeName.dump"
  if ($LASTEXITCODE -ne 0) { throw "pg_dump falló" }
  $port = if ($env:APP_PORT) { $env:APP_PORT } else { "8080" }
  try { Invoke-RestMethod "http://localhost:$port/api/settings" | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $backupDir "$safeName.settings.json") -Encoding utf8 } catch { Write-Warning "No se pudo exportar settings por API; la copia de la base sí los incluye." }
  try { Invoke-WebRequest "http://localhost:$port/api/players/export?format=csv" -OutFile (Join-Path $backupDir "$safeName.inventory.csv") } catch { Write-Warning "No se pudo crear el CSV adicional." }
  Write-Host "Copia creada en backups/$safeName.dump"
} finally { Pop-Location }
