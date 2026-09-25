@echo off
title AI Data Analyst OS - Startup Manager
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_app_on_boot.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo Startup encountered an error. Please check logs\startup.log
    pause
)
