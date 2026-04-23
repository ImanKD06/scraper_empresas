@echo off
chcp 65001 >nul
title CRM CNAE - Setup y Arranque
color 0B
cls

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║         CRM CNAE · Setup Windows            ║
echo  ║   MySQL Terminal + Python + FastAPI          ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ── Verificar Python ──────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado.
    echo  Descarga Python desde: https://python.org/downloads
    echo  Marca la casilla "Add Python to PATH" al instalar.
    pause
    exit /b
)
echo  [OK] Python encontrado

:: ── Verificar MySQL ────────────────────────────────────────
mysql --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [AVISO] MySQL no encontrado en PATH.
    echo  Si tienes MySQL instalado, añade su carpeta bin al PATH.
    echo  Normalmente: C:\Program Files\MySQL\MySQL Server 8.0\bin
    echo.
    echo  Si NO tienes MySQL, descarga MySQL Community:
    echo  https://dev.mysql.com/downloads/mysql/
    echo.
    echo  Una vez instalado, vuelve a ejecutar este archivo.
    pause
    exit /b
)
echo  [OK] MySQL encontrado

:: ── Instalar dependencias Python ──────────────────────────
echo.
echo  [1/3] Instalando dependencias Python...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet
echo  [OK] Dependencias instaladas

:: ── Crear base de datos MySQL ──────────────────────────────
echo.
echo  [2/3] Creando base de datos en MySQL...
echo  (Se pedira la contrasena de root de MySQL)
echo.
mysql -u root -p < "%~dp0crear_bd.sql"
if errorlevel 1 (
    echo.
    echo  [ERROR] No se pudo conectar a MySQL.
    echo  Verifica que MySQL esta corriendo y la contrasena es correcta.
    pause
    exit /b
)
echo  [OK] Base de datos creada correctamente

:: ── Arrancar servidor ──────────────────────────────────────
echo.
echo  [3/3] Arrancando servidor CRM...
echo.
echo  ┌─────────────────────────────────────────┐
echo  │  Servidor: http://localhost:8000         │
echo  │  Frontend: abrir frontend\index.html     │
echo  │  Login:    admin@crm.es / admin123       │
echo  │                                          │
echo  │  Ctrl+C para detener el servidor         │
echo  └─────────────────────────────────────────┘
echo.
cd /d "%~dp0backend"
python main.py
pause