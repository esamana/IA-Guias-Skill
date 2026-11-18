@echo off
rem Doble clic para instalar todo lo necesario (llama a instalar.ps1 sin pedir cambiar permisos de PowerShell).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
