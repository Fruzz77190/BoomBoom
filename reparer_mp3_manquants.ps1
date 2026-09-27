# Repare les telechargements incomplets (pochette webp sans MP3).
# Double-clic ou : powershell -ExecutionPolicy Bypass -File .\reparer_mp3_manquants.ps1

$ErrorActionPreference = "Continue"
$ScriptDir = $PSScriptRoot
Set-Location $ScriptDir

$python = $null
foreach ($cmd in @("py", "python", "python3")) {
    $exe = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($exe) { $python = $exe.Source; break }
}
if (-not $python) {
    Write-Host "Python introuvable." -ForegroundColor Red
    Read-Host "Entree pour fermer"
    exit 1
}

Write-Host "Mise a jour de yt-dlp..." -ForegroundColor Cyan
& $python -m pip install --upgrade yt-dlp 2>&1 | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "IMPORTANT : les MP3 vont ici (pas dans le dossier BoomBoom) :" -ForegroundColor Yellow
Write-Host "  $env:USERPROFILE\Desktop\Musique\Download\Boumboum" -ForegroundColor Yellow
Write-Host ""
Write-Host "Astuce 403 : connectez-vous a YouTube, fermez Edge/Chrome, puis relancez." -ForegroundColor Yellow
Write-Host "Voir COOKIES_README.txt pour exporter cookies.txt si besoin." -ForegroundColor Yellow
Write-Host ""
Write-Host "Reparation des MP3 manquants..." -ForegroundColor Cyan
& $python -c @"
import sys
sys.path.insert(0, r'$ScriptDir')
from telecharger_playlist import check_dependencies, ensure_baseline, repair_incomplete_downloads
check_dependencies()
ensure_baseline()
repair_incomplete_downloads()
"@

Write-Host ""
Read-Host "Appuyez sur Entree pour fermer"
