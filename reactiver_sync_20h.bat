@echo off
title Reactiver synchronisation 20h BoomBoom
schtasks /Change /TN "BoomBoom Sync Playlist" /ENABLE 2>nul
if errorlevel 1 (
    echo Tache introuvable. Lancez configurer_planification.bat
) else (
    echo Tache reactivee : synchronisation chaque jour a 20h.
)
echo.
pause
