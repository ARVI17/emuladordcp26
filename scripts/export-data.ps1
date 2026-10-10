$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "project-config.ps1")
$projectConfig = Get-ProjectConfig
$backupDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$appBaseUrl = $projectConfig.AppBaseUrl
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
Invoke-WebRequest "$appBaseUrl/api/players/export?format=csv" -OutFile (Join-Path $backupDir "inventory-$stamp.csv")
Invoke-WebRequest "$appBaseUrl/api/players/export?format=xlsx" -OutFile (Join-Path $backupDir "inventory-$stamp.xlsx")
Invoke-RestMethod "$appBaseUrl/api/settings" | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $backupDir "settings-$stamp.json") -Encoding utf8
Write-Host "Inventario y configuración exportados en $backupDir"
