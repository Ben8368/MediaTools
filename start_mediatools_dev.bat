@echo off
setlocal

cd /d "%~dp0"

set "URL=http://127.0.0.1:7860"
set "VITE_URL=http://127.0.0.1:5173"
set "PID_FILE=runtime\mediatools-web.pid"
set "LOG_FILE=runtime\mediatools-web.log"
set "ERR_FILE=runtime\mediatools-web.err.log"
set "VITE_PID_FILE=runtime\mediatools-vite.pid"
set "VITE_LOG_FILE=runtime\mediatools-vite.log"
set "VITE_ERR_FILE=runtime\mediatools-vite.err.log"

echo ========================================
echo Starting MediaTools Dev Mode
echo ========================================
echo.

if not exist runtime mkdir runtime

echo [1/4] Stopping existing MediaTools dev processes...
powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -Command "& { . '%~dp0scripts\dev-startup-helpers.ps1'; Stop-ProcessByPort -Ports @(7860, 5173) }"
if errorlevel 1 goto FAILED

del /f /q "%PID_FILE%" >nul 2>&1
del /f /q "%VITE_PID_FILE%" >nul 2>&1

echo [2/4] Launching backend and Vite in parallel...
powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -Command "& { . '%~dp0scripts\dev-startup-helpers.ps1'; $result = Start-BackendAndVite -RootDir '%cd%' -FrontendDir '%cd%\frontend' -ViteUrl '%VITE_URL%' -LogFile '%cd%\%LOG_FILE%' -ErrFile '%cd%\%ERR_FILE%' -ViteLogFile '%cd%\%VITE_LOG_FILE%' -ViteErrFile '%cd%\%VITE_ERR_FILE%' -PidFile '%cd%\%PID_FILE%' -VitePidFile '%cd%\%VITE_PID_FILE%'; if (-not $result) { exit 1 } }"
if errorlevel 1 goto FAILED

echo [3/4] Opening MediaTools...
start "" "%URL%"

echo.
echo Dev mode started at %URL%
echo Backend proxies frontend requests to %VITE_URL%
echo.
echo Press Ctrl+C to stop the server.
pause >nul
goto CLEANUP

:CLEANUP
echo Stopping dev processes...
powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -Command "& { . '%~dp0scripts\dev-startup-helpers.ps1'; Stop-ProcessByPort -Ports @(7860, 5173) }"
exit /b 0

:FAILED
echo.
echo MediaTools dev mode failed to start.
pause
exit /b 1
