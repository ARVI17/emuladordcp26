$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backupDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$port = if ($env:APP_PORT) { $env:APP_PORT } else { "8080" }
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
Invoke-WebRequest "http://localhost:$port/api/players/export?format=csv" -OutFile (Join-Path $backupDir "inventory-$stamp.csv")
Invoke-WebRequest "http://localhost:$port/api/players/export?format=xlsx" -OutFile (Join-Path $backupDir "inventory-$stamp.xlsx")
Invoke-RestMethod "http://localhost:$port/api/settings" | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $backupDir "settings-$stamp.json") -Encoding utf8
Write-Host "Inventario y configuración exportados en $backupDir"
