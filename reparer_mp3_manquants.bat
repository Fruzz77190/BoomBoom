@echo off
title Reparation MP3 BoomBoom
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reparer_mp3_manquants.ps1"
