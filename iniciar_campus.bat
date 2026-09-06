@echo off
setlocal
cd /d "%~dp0"

title Campus Virtual IES N5 Tello

echo ============================================================
echo           CAMPUS VIRTUAL - IES N 5 J. E. TELLO
echo ============================================================
echo.

if exist "venv\Scripts\python.exe" goto INICIAR

echo [1/2] Creando entorno virtual aislado...
python -m venv venv
if errorlevel 1 goto ERROR_VENV

echo [2/2] Instalando dependencias necesarias...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto ERROR_PIP

:INICIAR
echo [*] Iniciando Campus Virtual...
echo.
venv\Scripts\python.exe main.py
if errorlevel 1 goto ERROR_EJECUCION
exit /b 0

:ERROR_VENV
echo.
echo [ERROR] No se pudo crear el entorno virtual venv.
echo Asegurate de tener Python instalado y agregado al PATH.
pause
exit /b 1

:ERROR_PIP
echo.
echo [ERROR] No se pudieron instalar las dependencias.
pause
exit /b 1

:ERROR_EJECUCION
echo.
echo [AVISO] El programa se cerro con un codigo de salida inesperado.
pause
exit /b 1
