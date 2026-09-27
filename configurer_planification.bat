@echo off
title Configuration planification BoomBoom
cd /d "%~dp0"
echo.
echo Configuration de la tache planifiee (20h chaque jour)...
echo Ne fermez pas cette fenetre.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0configurer_planification.ps1"
echo.
pause
