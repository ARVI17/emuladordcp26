# Resolve exactly the same .env and shell overrides as Docker Compose.
function Get-ProjectConfig {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    Push-Location $projectRoot
    try {
        $resolvedJson = docker compose config --format json
        if ($LASTEXITCODE -ne 0) { throw "No se pudo resolver la configuración de Docker Compose." }
        $configuration = ($resolvedJson -join "`n") | ConvertFrom-Json
        $webPort = $configuration.services.nginx.ports | Where-Object { $_.target -eq 80 } | Select-Object -First 1
        if (-not $webPort) { throw "Docker Compose no publica el puerto web de Nginx." }
        $appPort = [string]$webPort.published
        $bindAddress = ([string]$webPort.host_ip).Trim()
        if ([string]::IsNullOrWhiteSpace($bindAddress) -or $bindAddress -in @("0.0.0.0", "::", "[::]")) {
            $uriAddress = "localhost"
        }
        else {
            $uriAddress = $bindAddress.TrimStart('[').TrimEnd(']')
            if ($uriAddress.Contains(':')) { $uriAddress = "[$uriAddress]" }
        }
        $appBaseUrl = "http://{0}:{1}" -f $uriAddress, $appPort
        return [PSCustomObject]@{
            DatabaseUser = [string]$configuration.services.database.environment.POSTGRES_USER
            DatabaseName = [string]$configuration.services.database.environment.POSTGRES_DB
            AppPort = $appPort
            AppBaseUrl = $appBaseUrl
        }
    } finally { Pop-Location }
}
