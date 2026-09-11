@echo off
chcp 65001 >nul
title Launcher IES N5
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ERROR: No se encontro el entorno virtual.
    pause
    exit /b 1
)

echo Iniciando Campus Virtual IES N5...
venv\Scripts\python.exe app_pyloid.py
