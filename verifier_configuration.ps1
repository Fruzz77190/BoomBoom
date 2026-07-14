# Verifie que la configuration BoomBoom est correcte pour la synchronisation automatique.

$ErrorActionPreference = "Continue"

$ScriptDir = $PSScriptRoot
$NomTache = "BoomBoom Sync Playlist"
$HeureAttendue = "20:00"
$DownloadDir = Join-Path $env:USERPROFILE "Desktop\Musique\Download\Boumboum"
$LogDir = Join-Path $DownloadDir "logs"
$ok = 0
$warn = 0
$err = 0

function Report-Ok { param([string]$Msg) Write-Host "[OK]   $Msg" -ForegroundColor Green; $script:ok++ }
function Report-Warn { param([string]$Msg) Write-Host "[WARN] $Msg" -ForegroundColor Yellow; $script:warn++ }
function Report-Err { param([string]$Msg) Write-Host "[ERR]  $Msg" -ForegroundColor Red; $script:err++ }

Write-Host "=== Verification configuration BoomBoom ===" -ForegroundColor Cyan
Write-Host ""

# Fichiers du projet
$requiredFiles = @(
    (Join-Path $ScriptDir "telecharger_playlist.py"),
    (Join-Path $ScriptDir "lancer_sync.ps1"),
    (Join-Path $ScriptDir "configurer_planification.ps1")
)
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Report-Ok "Fichier present : $(Split-Path $file -Leaf)"
    } else {
        Report-Err "Fichier manquant : $file"
    }
}

# Dossiers
if (Test-Path $DownloadDir) {
    Report-Ok "Dossier telechargement : $DownloadDir"
} else {
    Report-Warn "Dossier telechargement absent (sera cree au 1er lancement) : $DownloadDir"
}

if (Test-Path $LogDir) {
    $lastLog = Get-ChildItem -Path $LogDir -Filter "sync_*.log" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($lastLog) {
        Report-Ok "Dernier journal : $($lastLog.Name) ($($lastLog.LastWriteTime))"
    } else {
        Report-Warn "Aucun journal de synchronisation trouve"
    }
} else {
    Report-Warn "Dossier logs absent (sera cree au 1er lancement)"
}

# Dependances
$python = $null
foreach ($cmd in @("py", "python", "python3")) {
    $exe = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($exe) { $python = $exe.Source; break }
}
if ($python) {
    Report-Ok "Python : $python"
    & $python -c "import yt_dlp, mutagen" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Report-Ok "Modules Python : yt-dlp, mutagen"
    } else {
        Report-Err "Modules manquants. Lancez : pip install yt-dlp mutagen"
    }
} else {
    Report-Err "Python introuvable"
}

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Report-Ok "FFmpeg : $(Get-Command ffmpeg | Select-Object -ExpandProperty Source)"
} else {
    Report-Err "FFmpeg introuvable dans le PATH"
}

# Tache planifiee
$task = Get-ScheduledTask -TaskName $NomTache -ErrorAction SilentlyContinue
if (-not $task) {
    Report-Err "Tache planifiee '$NomTache' introuvable. Lancez configurer_planification.ps1"
} else {
    Report-Ok "Tache planifiee : $NomTache (Etat : $($task.State))"

    $trigger = $task.Triggers | Select-Object -First 1
    if ($trigger) {
        $heure = "{0:00}:{1:00}" -f $trigger.StartBoundary.Hour, $trigger.StartBoundary.Minute
        if ($heure -eq $HeureAttendue) {
            Report-Ok "Horaire : $heure (quotidien)"
        } else {
            Report-Warn "Horaire actuel : $heure (attendu : $HeureAttendue). Relancez configurer_planification.ps1"
        }
    }

    $action = $task.Actions | Select-Object -First 1
    if ($action -and $action.Arguments -like "*lancer_sync.ps1*") {
        Report-Ok "Action : lancer_sync.ps1"
    } else {
        Report-Warn "Action de la tache inattendue : $($action.Arguments)"
    }

    $settings = $task.Settings
    if ($settings.MultipleInstances -eq "IgnoreNew") {
        Report-Ok "Instances multiples : IgnoreNew"
    } else {
        Report-Warn "Instances multiples : $($settings.MultipleInstances) (recommande : IgnoreNew)"
    }
}

# Archive / baseline
$archive = Join-Path $DownloadDir "archive.txt"
$baseline = Join-Path $DownloadDir ".baseline_done"
$baselineIds = Join-Path $DownloadDir "baseline_ids.txt"
if (Test-Path $baseline) {
    Report-Ok "Baseline initialisee : $(Get-Content $baseline -TotalCount 1)"
} else {
    Report-Warn "Baseline non initialisee (normal au premier lancement)"
}
if (Test-Path $baselineIds) {
    $count = (Get-Content $baselineIds | Where-Object { $_.Trim() }).Count
    Report-Ok "baseline_ids.txt : $count video(s) ignorees"
}
if (Test-Path $archive) {
    $count = (Get-Content $archive | Where-Object { $_.Trim() }).Count
    Report-Ok "archive.txt : $count entree(s)"
}

Write-Host ""
Write-Host "=== Resume : $ok OK | $warn avertissement(s) | $err erreur(s) ===" -ForegroundColor Cyan

if ($err -gt 0) {
    exit 1
}
exit 0
