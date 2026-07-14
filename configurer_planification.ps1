# Configure une tache planifiee Windows pour lancer la synchronisation chaque jour a 20h.
# Executez ce script une seule fois :
#   Clic droit > Executer avec PowerShell

param(
    [string]$Heure = "20:00",
    [string]$NomTache = "BoomBoom Sync Playlist"
)

$ErrorActionPreference = "Stop"

$scriptSync = Join-Path $PSScriptRoot "lancer_sync.ps1"
$scriptDir = $PSScriptRoot

if (-not (Test-Path $scriptSync)) {
    Write-Error "Fichier introuvable : $scriptSync"
    exit 1
}

Write-Host "Configuration de la tache planifiee '$NomTache'..."
Write-Host "  Script    : $scriptSync"
Write-Host "  Repertoire: $scriptDir"
Write-Host "  Horaire   : chaque jour a $Heure (heure locale)"
Write-Host "  Utilisateur: $env:USERDOMAIN\$env:USERNAME"
Write-Host ""

$existante = Get-ScheduledTask -TaskName $NomTache -ErrorAction SilentlyContinue
if ($existante) {
    Write-Host "Suppression de l'ancienne tache..."
    Unregister-ScheduledTask -TaskName $NomTache -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptSync`"" `
    -WorkingDirectory $scriptDir

$trigger = New-ScheduledTaskTrigger -Daily -At $Heure

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $NomTache `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Telecharge les nouvelles videos de la playlist YouTube BoomBoom chaque jour a $Heure." | Out-Null

Write-Host "Tache planifiee creee avec succes !" -ForegroundColor Green
Write-Host ""
Write-Host "Verification :"
& (Join-Path $PSScriptRoot "verifier_configuration.ps1")
