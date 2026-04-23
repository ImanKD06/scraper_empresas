@echo off
chcp 65001 >nul
title CRM CNAE
color 0A
cls
echo.
echo  CRM CNAE - Arrancando...
echo  Frontend: abre frontend\index.html en Chrome/Edge
echo  Login: admin@crm.es / admin123
echo  Ctrl+C para parar
echo.
cd /d "%~dp0backend"
python main.py
pause