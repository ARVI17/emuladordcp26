[CmdletBinding()]
param([string]$AvdName = "FC26_Companion")

$ErrorActionPreference = "Stop"
$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $adb)) {
    throw "No se encontró ADB: $adb"
}

$serial = $null
foreach ($row in (& $adb devices)) {
    if ($row -notmatch '^(emulator-\d+)\s+device$') { continue }
    $candidate = $Matches[1]
    $reportedName = (& $adb -s $candidate emu avd name 2>$null | Select-Object -First 1).Trim()
    if ($reportedName -eq $AvdName) { $serial = $candidate; break }
}

if (-not $serial) {
    Write-Host "$AvdName no está iniciado."
    exit 0
}

& $adb -s $serial emu kill | Out-Host
$deadline = (Get-Date).AddSeconds(30)
while ((Get-Process -Name "qemu-system-x86_64" -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 1
}
if (Get-Process -Name "qemu-system-x86_64" -ErrorAction SilentlyContinue) {
    throw "El AVD no se detuvo dentro de 30 segundos."
}

& $adb kill-server 2>$null
Write-Host "$AvdName detenido; su memoria fue liberada. Los contenedores del proyecto siguen activos."
