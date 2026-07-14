# Installation automatique en un clic : dependances + tache planifiee 20h + test.

$ErrorActionPreference = "Continue"
$ScriptDir = $PSScriptRoot
$LogFile = Join-Path $ScriptDir "install_log.txt"

function Write-Step {
    param([string]$Message)
    $line = ">>> $Message"
    Write-Host ""
    Write-Host $line -ForegroundColor Cyan
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Write-Log {
    param([string]$Message)
    Write-Host $Message
    Add-Content -Path $LogFile -Value $Message -Encoding UTF8
}

function Find-Python {
    foreach ($cmd in @("py", "python", "python3")) {
        $exe = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($exe) { return $exe.Source }
    }
    return $null
}

function Wait-Key {
    Write-Host ""
    Read-Host "Appuyez sur Entree pour fermer cette fenetre"
}

try {
    Set-Location $ScriptDir
    "=== Installation BoomBoom - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Set-Content $LogFile -Encoding UTF8

    Write-Log "========================================"
    Write-Log "  INSTALLATION BOOMBOOM - Automatique"
    Write-Log "========================================"
    Write-Log "Dossier : $ScriptDir"

    # 1. Python
    Write-Step "Verification de Python..."
    $python = Find-Python
    if (-not $python) {
        Write-Log "ERREUR : Python n'est pas installe."
        Write-Log "Installez-le sur https://www.python.org/downloads/"
        Write-Log "Cochez 'Add Python to PATH' pendant l'installation."
        Wait-Key
        exit 1
    }
    Write-Log "Python trouve : $python"

    # 2. Modules Python
    Write-Step "Installation des modules Python (yt-dlp, mutagen)..."
    & $python -m pip install --upgrade yt-dlp mutagen 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Tentative pip direct..."
        pip install --upgrade yt-dlp mutagen 2>&1 | ForEach-Object { Write-Log $_ }
    }

    # 3. FFmpeg
    Write-Step "Verification de FFmpeg..."
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Write-Log "FFmpeg absent. Telechargement en cours..."
        Write-Log "PATIENTEZ : fichier volumineux (~220 Mo), cela peut prendre 5 a 10 minutes."
        Write-Log "Ne fermez pas cette fenetre pendant l'extraction."
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements 2>&1 |
                ForEach-Object { Write-Log $_ }
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
        }
        if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
            Write-Log "ATTENTION : FFmpeg toujours introuvable."
            Write-Log "Installez-le : winget install Gyan.FFmpeg"
        } else {
            Write-Log "FFmpeg installe."
        }
    } else {
        Write-Log "FFmpeg trouve."
    }

    # 4. Dossier de telechargement
    Write-Step "Creation du dossier de telechargement..."
    $downloadDir = Join-Path $env:USERPROFILE "Desktop\Musique\Download\Boumboum"
    New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
    Write-Log "Dossier : $downloadDir"

    # 5. Tache planifiee 20h
    Write-Step "Configuration de la tache planifiee (chaque jour a 20h)..."
    $configScript = Join-Path $ScriptDir "configurer_planification.ps1"
    if (-not (Test-Path $configScript)) {
        throw "Fichier manquant : configurer_planification.ps1"
    }
    & $configScript 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "Echec de configurer_planification.ps1 (code $LASTEXITCODE)"
    }

    # 6. Premier test
    Write-Step "Lancement d'un test de synchronisation..."
    $syncScript = Join-Path $ScriptDir "lancer_sync.ps1"
    if (-not (Test-Path $syncScript)) {
        throw "Fichier manquant : lancer_sync.ps1"
    }
    & $syncScript 2>&1 | ForEach-Object { Write-Log $_ }

    Write-Log ""
    Write-Log "========================================"
    Write-Log "  INSTALLATION TERMINEE AVEC SUCCES !"
    Write-Log "========================================"
    Write-Log "Synchronisation automatique chaque jour a 20h."
    Write-Log "MP3 : $downloadDir"
    Write-Log "Logs : $downloadDir\logs\"
    Write-Log "Journal installation : $LogFile"
    Wait-Key
    exit 0
}
catch {
    Write-Log ""
    Write-Log "ERREUR FATALE : $_"
    Write-Log "Consultez le fichier : $LogFile"
    Wait-Key
    exit 1
}
