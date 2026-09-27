# Repare les telechargements incomplets (pochette webp sans MP3).

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
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

Write-Host ""
Write-Host "IMPORTANT : les MP3 vont ici (pas dans le dossier BoomBoom) :" -ForegroundColor Yellow
Write-Host "  $env:USERPROFILE\Desktop\Musique\Download\Boumboum" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ne fermez pas cette fenetre pendant le telechargement." -ForegroundColor Cyan
Write-Host "(Cela peut prendre plusieurs minutes.)" -ForegroundColor Cyan
Write-Host ""

$scriptPy = Join-Path $ScriptDir "telecharger_playlist.py"
& $python $scriptPy --repair-only
$code = $LASTEXITCODE

Write-Host ""
if ($code -ne 0) {
    Write-Host "Des erreurs sont survenues. Lisez les messages ci-dessus." -ForegroundColor Red
    Write-Host "Astuce 403 : connectez-vous a YouTube, fermez Edge/Chrome, relancez." -ForegroundColor Yellow
    Write-Host "Voir COOKIES_README.txt pour le fichier cookies.txt." -ForegroundColor Yellow
} else {
    Write-Host "Verifiez le dossier Boumboum sur votre Bureau." -ForegroundColor Green
}

Write-Host ""
Read-Host "Appuyez sur Entree pour fermer"
exit $code
