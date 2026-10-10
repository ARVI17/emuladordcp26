param([Parameter(Mandatory=$true)][string]$BackupFile)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "project-config.ps1")
$projectConfig = Get-ProjectConfig
$backupDir = [System.IO.Path]::GetFullPath((Join-Path $root "backups"))
$resolved = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $BackupFile).Path)
$pathComparison = if ([System.IO.Path]::DirectorySeparatorChar -eq '\') { [System.StringComparison]::OrdinalIgnoreCase } else { [System.StringComparison]::Ordinal }
if (-not $resolved.StartsWith($backupDir + [System.IO.Path]::DirectorySeparatorChar, $pathComparison)) { throw "La copia debe estar dentro de $backupDir" }
if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "La copia debe ser un archivo." }
if ([System.IO.Path]::GetExtension($resolved) -ne ".dump") { throw "Se requiere un archivo .dump" }
$dbUser = $projectConfig.DatabaseUser
$dbName = $projectConfig.DatabaseName
$safeBefore = "before-restore-$(Get-Date -Format 'yyyyMMdd-HHmmss').dump"
# Preserve the chosen file's complete relative path, including nested folders,
# spaces and hyphens. GetFullPath and the prefix guard above reject traversal.
$relativeBackupPath = $resolved.Substring($backupDir.Length + 1).Replace('\', '/')
$containerPath = "/backups/" + $relativeBackupPath
Push-Location $root
try {
  docker compose exec -T database pg_dump -U $dbUser -d $dbName -Fc -f "/backups/$safeBefore"
  if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la copia de seguridad previa" }
  docker compose stop backend
  if ($LASTEXITCODE -ne 0) { throw "No se pudo detener el backend antes de restaurar." }
  try {
    docker compose exec -T database pg_restore -U $dbUser -d $dbName --clean --if-exists --no-owner --single-transaction --exit-on-error $containerPath
    if ($LASTEXITCODE -ne 0) { throw "La restauración se revirtió; se conserva backups/$safeBefore" }
  } finally {
    docker compose start backend
    if ($LASTEXITCODE -ne 0) { Write-Warning "El backend requiere un arranque manual: docker compose start backend" }
  }
  Write-Host "Restauración completada. Copia previa: backups/$safeBefore"
} finally { Pop-Location }
