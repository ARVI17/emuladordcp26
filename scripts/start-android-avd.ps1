[CmdletBinding()]
param(
    [string]$AvdName = "FC26_Companion",
    [ValidateRange(1536, 4096)]
    [int]$MemoryMb = 1536,
    [ValidateRange(1, 4)]
    [int]$Cores = 2,
    [switch]$ColdBoot
)

$ErrorActionPreference = "Stop"
$sdkRoot = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$adb = Join-Path $sdkRoot "platform-tools\adb.exe"
$emulator = Join-Path $sdkRoot "emulator\emulator.exe"

foreach ($required in @($adb, $emulator)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Falta una herramienta Android: $required"
    }
}

if (-not ((& $emulator -list-avds) -contains $AvdName)) {
    throw "No existe el AVD '$AvdName'. Ábrelo una vez desde Android Studio > Device Manager."
}

# El servidor ADB permanece en loopback. Docker Desktop lo alcanza mediante
# host.docker.internal, sin exponer el puerto 5037 a la red local.
& $adb start-server | Out-Host

function Find-AvdSerial {
    $rows = & $adb devices
    foreach ($row in $rows) {
        if ($row -notmatch '^(emulator-\d+)\s+device$') { continue }
        $candidate = $Matches[1]
        $reportedName = (& $adb -s $candidate emu avd name 2>$null | Select-Object -First 1).Trim()
        if ($reportedName -eq $AvdName) { return $candidate }
    }
    return $null
}

$serial = Find-AvdSerial
if (-not $serial) {
    $arguments = @(
        "-avd", $AvdName,
        "-memory", $MemoryMb,
        "-cores", $Cores,
        "-gpu", "host",
        "-no-audio",
        "-no-boot-anim",
        "-netdelay", "none",
        "-netspeed", "full"
    )
    if ($ColdBoot) { $arguments += "-no-snapshot-load" }
    Start-Process -FilePath $emulator -ArgumentList $arguments | Out-Null
    Write-Host "Iniciando $AvdName en una ventana visible..."
}
else {
    Write-Host "$AvdName ya está iniciado como $serial."
}

$deadline = (Get-Date).AddMinutes(4)
do {
    if (-not $serial) { $serial = Find-AvdSerial }
    if ($serial) {
        $bootCompleted = ((& $adb -s $serial shell getprop sys.boot_completed 2>$null) -join '').Trim()
        $bootAnimation = ((& $adb -s $serial shell getprop init.svc.bootanim 2>$null) -join '').Trim()
        if ($bootCompleted -eq "1" -and $bootAnimation -eq "stopped") { break }
    }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

if (-not $serial -or $bootCompleted -ne "1") {
    throw "Android no terminó de iniciar dentro de cuatro minutos. Revisa la ventana del emulador."
}

# El panel mantiene proporción Pixel 5, pero renderiza menos píxeles y usa
# animaciones cortas para reducir GPU/RAM sin alterar la compatibilidad Android.
& $adb -s $serial shell wm size 720x1560 | Out-Null
& $adb -s $serial shell wm density 300 | Out-Null
& $adb -s $serial shell cmd uimode night yes | Out-Null
& $adb -s $serial shell settings put global window_animation_scale 0.5 | Out-Null
& $adb -s $serial shell settings put global transition_animation_scale 0.5 | Out-Null
& $adb -s $serial shell settings put global animator_duration_scale 0.5 | Out-Null

# Este AVD está dedicado a Companion. Se mantienen Play Store, Chrome y Google
# Play Services; se apagan apps de teléfono que solo agregan procesos y ruido.
$unusedPackages = @(
    "com.google.android.apps.wellbeing",
    "com.google.android.googlequicksearchbox",
    "com.google.android.tts",
    "com.google.android.apps.messaging",
    "com.google.android.as",
    "com.google.android.gm",
    "com.google.android.apps.photos",
    "com.google.android.youtube"
)
foreach ($package in $unusedPackages) {
    & $adb -s $serial shell pm disable-user --user 0 $package 2>$null | Out-Null
}

Write-Host "Android listo: $serial ($MemoryMb MB, $Cores núcleos, 720x1560, modo oscuro)."

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $backendId = docker compose ps -q backend 2>$null
    if ($backendId) {
        $payload = @{ serial = $serial } | ConvertTo-Json -Compress
        $selection = Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/emulator/select" -ContentType "application/json" -Body $payload -TimeoutSec 15
        if ($selection.selected) {
            Write-Host "AVD seleccionado en Asistente FC 26. Abre http://localhost:8080"
        }
    }
    else {
        Write-Host "El AVD está listo. Inicia el proyecto con: docker compose up --build -d"
    }
}
catch {
    Write-Warning "El AVD está listo, pero el backend aún no pudo seleccionarlo: $($_.Exception.Message)"
}
finally {
    Pop-Location
}
