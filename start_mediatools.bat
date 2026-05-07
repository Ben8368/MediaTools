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
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '.').Path; $pidFile=Join-Path $root '%PID_FILE%'; $listener=@(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); if ($listener.Count -gt 0) { foreach ($listenPid in $listener) { $proc=Get-CimInstance Win32_Process -Filter \"ProcessId=$listenPid\" -ErrorAction SilentlyContinue; if ($proc -and $proc.Name -match '^python' -and $proc.CommandLine -like '*app.py*') { Write-Host \"MediaTools backend already running on port 7860. PID=$listenPid\"; Set-Content -LiteralPath $pidFile -Value $listenPid -Encoding ascii; exit 10 } else { Write-Host \"Port 7860 is already used by another process. PID=$listenPid\"; exit 20 } } }; exit 0"
if "%ERRORLEVEL%"=="10" goto OPEN_EXISTING
if "%ERRORLEVEL%"=="20" goto PORT_BUSY
if errorlevel 1 goto FAILED

echo [2/4] Launching backend with watchdog...
:WATCHDOG_LOOP
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '.').Path; $pidFile=Join-Path $root '%PID_FILE%'; $logFile=Join-Path $root '%LOG_FILE%'; $errFile=Join-Path $root '%ERR_FILE%'; Remove-Item -LiteralPath $logFile -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue; $env:LOG_MODE='production'; $proc=Start-Process -FilePath 'python' -ArgumentList 'app.py' -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errFile; Set-Content -LiteralPath $pidFile -Value $proc.Id -Encoding ascii; Write-Host \"MediaTools backend started. PID=$($proc.Id)\"; Start-Sleep -Seconds 2; if ($proc.HasExited) { Write-Host \"MediaTools backend failed to start. ExitCode=$($proc.ExitCode). See %ERR_FILE%\"; exit 1 }; if ('%BROWSER_OPENED%' -ne '1') { Write-Host '[3/4] Opening WebUI...'; Start-Process '%URL%' }; $proc.WaitForExit(); exit $proc.ExitCode"
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
