@echo off
title Verification BoomBoom
cd /d "%~dp0"
echo.
echo Verification de la configuration...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verifier_configuration.ps1"
echo.
if exist "%~dp0install_log.txt" (
    echo --- Dernier journal d installation ---
    type "%~dp0install_log.txt"
    echo.
)
pause
