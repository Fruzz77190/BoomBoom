@echo off
title Installation BoomBoom
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_tout.ps1"
