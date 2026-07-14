# Configure une tache planifiee Windows pour lancer la synchronisation chaque jour a 20h.
# Executez ce script une seule fois en tant qu'administrateur ou utilisateur standard :
#   Clic droit > Executer avec PowerShell

param(
    [string]$Heure = "20:00",
    [string]$NomTache = "BoomBoom Sync Playlist"
)

$ErrorActionPreference = "Stop"

$scriptSync = Join-Path $PSScriptRoot "lancer_sync.ps1"

if (-not (Test-Path $scriptSync)) {
    Write-Error "Fichier introuvable : $scriptSync"
    exit 1
}

Write-Host "Configuration de la tache planifiee '$NomTache'..."
Write-Host "  Script  : $scriptSync"
Write-Host "  Horaire : chaque jour a $Heure"
Write-Host ""

$existante = Get-ScheduledTask -TaskName $NomTache -ErrorAction SilentlyContinue
if ($existante) {
    Write-Host "Suppression de l'ancienne tache..."
    Unregister-ScheduledTask -TaskName $NomTache -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptSync`""

$trigger = New-ScheduledTaskTrigger -Daily -At $Heure

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

Register-ScheduledTask `
    -TaskName $NomTache `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Telecharge les nouvelles videos de la playlist YouTube BoomBoom chaque jour a $Heure." `
    -RunLevel Limited | Out-Null

Write-Host "Tache planifiee creee avec succes !" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines etapes :"
Write-Host "  1. Verifiez dans le Planificateur de taches Windows (taskschd.msc)"
Write-Host "  2. Test manuel : clic droit sur la tache > Executer"
Write-Host "     ou lancez : .\lancer_sync.ps1"
Write-Host "  3. Les journaux sont dans :"
Write-Host "     $env:USERPROFILE\Desktop\Musique\Download\Boumboum\logs\"
