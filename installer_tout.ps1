# Installation automatique en un clic : dependances + tache planifiee 20h + test.
# Appele par INSTALLER.bat — ne pas lancer manuellement sauf besoin.

$ErrorActionPreference = "Continue"
$ScriptDir = $PSScriptRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host ">>> $Message" -ForegroundColor Cyan
}

function Find-Python {
    foreach ($cmd in @("py", "python", "python3")) {
        $exe = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($exe) { return $exe.Source }
    }
    return $null
}

Set-Location $ScriptDir

Write-Host "========================================" -ForegroundColor Green
Write-Host "  INSTALLATION BOOMBOOM - Automatique" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# 1. Python
Write-Step "Verification de Python..."
$python = Find-Python
if (-not $python) {
    Write-Host ""
    Write-Host "ERREUR : Python n'est pas installe." -ForegroundColor Red
    Write-Host "Installez-le ici puis relancez INSTALLER.bat :" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "(Cochez 'Add Python to PATH' pendant l'installation)" -ForegroundColor Yellow
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}
Write-Host "Python trouve : $python" -ForegroundColor Green

# 2. Modules Python
Write-Step "Installation des modules Python (yt-dlp, mutagen)..."
& $python -m pip install --upgrade yt-dlp mutagen 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Host "Attention : probleme pip. Tentative avec pip direct..." -ForegroundColor Yellow
    pip install --upgrade yt-dlp mutagen 2>&1 | ForEach-Object { Write-Host $_ }
}

# 3. FFmpeg
Write-Step "Verification de FFmpeg..."
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "FFmpeg absent. Tentative d'installation via winget..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements 2>&1 | ForEach-Object { Write-Host $_ }
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "ATTENTION : FFmpeg toujours introuvable." -ForegroundColor Yellow
        Write-Host "Installez-le manuellement : https://ffmpeg.org/download.html" -ForegroundColor Yellow
        Write-Host "Ou dans PowerShell admin : winget install Gyan.FFmpeg" -ForegroundColor Yellow
    } else {
        Write-Host "FFmpeg installe." -ForegroundColor Green
    }
} else {
    Write-Host "FFmpeg trouve." -ForegroundColor Green
}

# 4. Dossier de telechargement
Write-Step "Creation du dossier de telechargement..."
$downloadDir = Join-Path $env:USERPROFILE "Desktop\Musique\Download\Boumboum"
New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
Write-Host "Dossier : $downloadDir" -ForegroundColor Green

# 5. Tache planifiee 20h
Write-Step "Configuration de la tache planifiee (chaque jour a 20h)..."
& (Join-Path $ScriptDir "configurer_planification.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erreur lors de la configuration de la tache planifiee." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# 6. Premier test
Write-Step "Lancement d'un test de synchronisation..."
& (Join-Path $ScriptDir "lancer_sync.ps1")

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  INSTALLATION TERMINEE !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "La synchronisation tournera automatiquement chaque jour a 20h."
Write-Host "MP3 telecharges dans :"
Write-Host "  $downloadDir"
Write-Host ""
Write-Host "Journaux dans :"
Write-Host "  $downloadDir\logs\"
Write-Host ""
Read-Host "Appuyez sur Entree pour fermer"
