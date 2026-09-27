@echo off
title Arret synchronisation BoomBoom
echo Arret des processus Python / FFmpeg en cours...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM py.exe /T 2>nul
taskkill /F /IM ffmpeg.exe /T 2>nul
echo.
echo Arret de la tache planifiee en cours (si active)...
schtasks /End /TN "BoomBoom Sync Playlist" 2>nul
echo.
echo Termine. Vous pouvez fermer cette fenetre.
pause
