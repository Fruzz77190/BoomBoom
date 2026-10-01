@echo off
title Pause synchronisation 20h BoomBoom
echo Desactivation de la tache planifiee "BoomBoom Sync Playlist"...
schtasks /End /TN "BoomBoom Sync Playlist" 2>nul
schtasks /Change /TN "BoomBoom Sync Playlist" /DISABLE 2>nul
if errorlevel 1 (
    echo La tache planifiee est introuvable. Lancez configurer_planification.bat une fois.
) else (
    echo Tache desactivee. Plus de lancement automatique a 20h.
    echo Pour reactiver : reactiver_sync_20h.bat
)
echo.
pause
