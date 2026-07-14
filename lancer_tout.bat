@echo off
title Synchronisation BoomBoom
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0lancer_sync.ps1"
pause
