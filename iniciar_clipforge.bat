@echo off
title ClipForge AI - Servidor Local
chcp 65001 > nul
cls

echo ===============================================================
echo             ClipForge AI - Modo Local (Sin Bloqueos)
echo ===============================================================
echo.
echo Iniciando el servidor en tu computadora local...
echo Tu conexion residencial no sufre bloqueos de YouTube.
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual en .\venv.
    echo Por favor ejecuta la instalacion de dependencias primero.
    pause
    exit /b 1
)

start "" http://localhost:7860

echo Servidor activo en http://localhost:7860
echo Abre tu navegador y procesa tus videos sin problemas.
echo Presiona CTRL + C en esta ventana para detener el servidor.
echo.

venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 7860 --reload
pause
