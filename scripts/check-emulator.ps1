param(
    [string]$Address = "host.docker.internal:5555",
    [switch]$Connect
)

$ErrorActionPreference = "Stop"

if ($Address -notmatch '^[A-Za-z0-9._-]+:[0-9]{1,5}$') {
    throw "Dirección ADB inválida. Usa host:puerto, por ejemplo host.docker.internal:5555."
}

$backendId = docker compose ps -q backend
if (-not $backendId) {
    throw "El backend no está iniciado. Ejecuta: docker compose up --build -d"
}

if ($Connect) {
    Write-Host "Conectando ADB a $Address..."
    docker compose exec -T backend adb connect $Address
}

Write-Host "Dispositivos vistos por el contenedor backend:"
docker compose exec -T backend adb devices -l

Write-Host "Estado expuesto por la aplicación:"
$status = Invoke-RestMethod -Uri "http://localhost:8080/api/emulator/status"
$status | ConvertTo-Json -Depth 6
