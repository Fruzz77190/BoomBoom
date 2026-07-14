@echo off
title Installation BoomBoom
cd /d "%~dp0"
echo.
echo ========================================
echo   INSTALLATION BOOMBOOM
echo   Ne fermez pas cette fenetre !
echo ========================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_tout.ps1"
echo.
if errorlevel 1 (
    echo ERREUR - Consultez install_log.txt dans ce dossier.
) else (
    echo Installation terminee.
)
echo.
pause
