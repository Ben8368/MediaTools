@echo off
setlocal

cd /d "%~dp0"

set "URL=http://127.0.0.1:7860"
set "PID_FILE=runtime\mediatools-web.pid"
set "LOG_FILE=runtime\mediatools-web.log"
set "ERR_FILE=runtime\mediatools-web.err.log"
set "BROWSER_OPENED=0"

echo ========================================
echo Starting MediaTools WebUI
echo ========================================
echo.

if not exist runtime mkdir runtime

echo [1/4] Building frontend...
cd frontend
call npm run build >nul 2>&1
if errorlevel 1 (
    echo Warning: Frontend build failed. Continuing with existing build...
)
cd ..

echo [2/4] Checking existing MediaTools backend...
powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -Command "& { . '%~dp0scripts\dev-startup-helpers.ps1'; exit (Test-ExistingMediaToolsBackend -PidFile '%cd%\%PID_FILE%' -Port 7860) }"
if "%ERRORLEVEL%"=="10" goto OPEN_EXISTING
if "%ERRORLEVEL%"=="20" goto PORT_BUSY
if errorlevel 1 goto FAILED

echo [2/4] Launching backend with watchdog...
:WATCHDOG_LOOP
powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -Command "& { . '%~dp0scripts\dev-startup-helpers.ps1'; exit (Invoke-MediaToolsBackendWatchdogCycle -RootDir '%cd%' -PidFile '%cd%\%PID_FILE%' -LogFile '%cd%\%LOG_FILE%' -ErrFile '%cd%\%ERR_FILE%' -Url '%URL%' -OpenBrowser ('%BROWSER_OPENED%' -ne '1')) }"
set EXIT_CODE=%ERRORLEVEL%
if "%BROWSER_OPENED%"=="0" set "BROWSER_OPENED=1"
if "%EXIT_CODE%"=="3" (
    echo Backend requested restart. Restarting in 2 seconds...
    timeout /t 2 /nobreak >nul
    goto WATCHDOG_LOOP
)
if "%EXIT_CODE%"=="0" goto WATCHDOG_EXIT
goto FAILED

:WATCHDOG_EXIT
echo Backend exited normally.
exit /b 0

:OPEN_EXISTING
echo [2/4] Backend is already running.
echo [3/4] Opening WebUI...
start "" "%URL%"

echo.
echo MediaTools WebUI is already running at %URL%
echo PID file: %PID_FILE%
echo Log file: %LOG_FILE%
echo Error log: %ERR_FILE%
echo.
exit /b 0

:PORT_BUSY
echo.
echo Port 7860 is already used by a non-MediaTools process.
echo Close that process or change GUI_SERVER_PORT before starting MediaTools.
pause
exit /b 1

:FAILED
echo.
echo MediaTools WebUI failed to start.
echo Please check the log output above.
pause
exit /b 1
