[CmdletBinding()]
param([ValidateSet('Inicio','Estado','Pruebas','Parada')][string]$Accion = 'Estado')
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
function Invoke-Docker([string[]]$Arguments) {
    $result = & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker falló (código $LASTEXITCODE)." }
    return $result
}
if ($Accion -eq 'Pruebas') {
    & python (Join-Path $projectRoot 'scripts/verify_docker.py') --scope full
    if ($LASTEXITCODE -ne 0) { throw 'La verificación aislada falló.' }
    exit 0
}
$context = (Invoke-Docker @('context','show')).Trim()
$contextInfo = (Invoke-Docker @('context','inspect',$context) | Out-String | ConvertFrom-Json)[0]
if ($contextInfo.Endpoints.docker.Host -notmatch '^(npipe|unix)://') { throw 'Selecciona el motor Docker local.' }
$prefix = @('--context',$context)
$ids = @(Invoke-Docker ($prefix + @('ps','-aq','--no-trunc','--filter','label=com.docker.compose.project=emuladordcp26')))
if ($ids.Count -eq 0) { throw 'No existe la instalación principal. Inicio no crea ni migra instalaciones; usa el procedimiento de despliegue revisado.' }
$containers = Invoke-Docker ($prefix + @('inspect') + $ids) | Out-String | ConvertFrom-Json
$services = @{}
foreach ($container in $containers) {
    $service = $container.Config.Labels.'com.docker.compose.service'
    if ($services.ContainsKey($service)) { throw "Servicio duplicado: $service. Se conserva para revisión." }
    $services[$service] = $container
}
foreach ($required in @('database','backend','frontend','nginx')) {
    if (-not $services.ContainsKey($required)) { throw "Falta $required; no se recrea automáticamente." }
}
$pgMount = @($services.database.Mounts | Where-Object { $_.Type -eq 'volume' -and $_.Name -eq 'emuladordcp26_postgres_data' -and $_.Destination -eq '/var/lib/postgresql/data' })
if ($pgMount.Count -ne 1) { throw 'No se acredita el volumen persistente principal.' }
$binding = @($services.nginx.HostConfig.PortBindings.'80/tcp')
if ($binding.Count -ne 1 -or $binding[0].HostIp -notin @('127.0.0.1','::1')) { throw 'La entrada principal debe tener un único puerto local.' }
$appPort = 0
if (-not [int]::TryParse($binding[0].HostPort, [ref]$appPort) -or $appPort -lt 1024 -or $appPort -gt 65535) { throw 'Puerto principal no válido.' }
$appAddress = if ($binding[0].HostIp -eq '::1') { '[::1]' } else { '127.0.0.1' }
$appBaseUrl = "http://${appAddress}:$appPort"
$otherIds = @(Invoke-Docker ($prefix + @('ps','-aq','--no-trunc','--filter','label=com.docker.compose.project')))
if ($otherIds.Count) {
    $other = Invoke-Docker ($prefix + @('inspect') + $otherIds) | Out-String | ConvertFrom-Json
    foreach ($container in $other) {
        $name = $container.Config.Labels.'com.docker.compose.project'
        if ($name -like 'emuladordcp26*' -and $name -ne 'emuladordcp26' -and $name -notlike 'emuladordcp26-check-*') {
            if ($Accion -eq 'Inicio') { throw "Existe otro proyecto FC27 ($name). Hay que acreditar sus datos antes de retirarlo." }
            Write-Warning "Proyecto adicional pendiente de revisión: $name"
        }
        if ($container.Id -notin $ids -and $container.State.Running) {
            foreach ($ports in $container.HostConfig.PortBindings.PSObject.Properties) {
                if (@($ports.Value | Where-Object { $_.HostPort -eq [string]$appPort }).Count) { throw 'Otro contenedor ocupa el puerto principal.' }
            }
        }
    }
}
if ($Accion -eq 'Inicio') {
    foreach ($service in @('database','ollama','backend','frontend','nginx')) {
        if ($services.ContainsKey($service) -and -not $services[$service].State.Running) {
            Invoke-Docker ($prefix + @('start',$services[$service].Id)) | Out-Null
        }
    }
}
if ($Accion -eq 'Parada') {
    foreach ($service in @('nginx','frontend','backend','ollama','database')) {
        if ($services.ContainsKey($service) -and $services[$service].State.Running) {
            Invoke-Docker ($prefix + @('stop','--time','30',$services[$service].Id)) | Out-Null
        }
    }
}
Write-Output "FC27 personal: http://localhost:$appPort | Proyecto: emuladordcp26"
Write-Output 'Persistencia: emuladordcp26_postgres_data (se conserva)'
$current = Invoke-Docker ($prefix + @('inspect') + $ids) | Out-String | ConvertFrom-Json
foreach ($container in $current) {
    Write-Output ("{0}: {1} | {2}" -f $container.Config.Labels.'com.docker.compose.service',$container.State.Status,$container.Image)
}
if ($Accion -ne 'Parada') {
    try {
        $build = Invoke-RestMethod "$appBaseUrl/api/build" -TimeoutSec 10
        Write-Output ("Versión servida: {0} | {1}" -f $build.revision,$build.environment)
    } catch { Write-Warning 'La API todavía no responde; no se acredita la versión servida.' }
}
