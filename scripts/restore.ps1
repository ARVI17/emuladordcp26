param([Parameter(Mandatory=$true)][string]$BackupFile)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backupDir = [System.IO.Path]::GetFullPath((Join-Path $root "backups"))
$resolved = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $BackupFile).Path)
if (-not $resolved.StartsWith($backupDir + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw "La copia debe estar dentro de $backupDir" }
if ([System.IO.Path]::GetExtension($resolved) -ne ".dump") { throw "Se requiere un archivo .dump" }
$dbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "fc26" }
$dbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "fc26" }
$safeBefore = "before-restore-$(Get-Date -Format 'yyyyMMdd-HHmmss').dump"
$containerPath = "/backups/" + [System.IO.Path]::GetFileName($resolved)
Push-Location $root
try {
  docker compose exec -T database pg_dump -U $dbUser -d $dbName -Fc -f "/backups/$safeBefore"
  if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la copia de seguridad previa" }
  docker compose exec -T database pg_restore -U $dbUser -d $dbName --clean --if-exists --no-owner $containerPath
  if ($LASTEXITCODE -ne 0) { throw "La restauración falló; se conserva backups/$safeBefore" }
  docker compose restart backend
  Write-Host "Restauración completada. Copia previa: backups/$safeBefore"
} finally { Pop-Location }
