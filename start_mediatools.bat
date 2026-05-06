@echo off
setlocal

cd /d "%~dp0"

set "URL=http://127.0.0.1:7860"
set "PID_FILE=runtime\mediatools-web.pid"
set "LOG_FILE=runtime\mediatools-web.log"
set "ERR_FILE=runtime\mediatools-web.err.log"

echo ========================================
echo Starting MediaTools WebUI
echo ========================================
echo.

if not exist runtime mkdir runtime

echo [1/3] Checking existing MediaTools backend...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '.').Path; $pidFile=Join-Path $root '%PID_FILE%'; if (Test-Path -LiteralPath $pidFile) { $oldPid=0; [int]::TryParse((Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1), [ref]$oldPid) | Out-Null; if ($oldPid -gt 0) { $proc=Get-CimInstance Win32_Process -Filter \"ProcessId=$oldPid\" -ErrorAction SilentlyContinue; if ($proc -and $proc.CommandLine -like \"*$root*\" -and $proc.CommandLine -like \"*app.py*\") { Write-Host \"MediaTools backend already running. PID=$oldPid\"; exit 10 } } }; $listener=@(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); if ($listener.Count -gt 0) { foreach ($pid in $listener) { $proc=Get-CimInstance Win32_Process -Filter \"ProcessId=$pid\" -ErrorAction SilentlyContinue; if ($proc -and $proc.CommandLine -like \"*$root*\") { Write-Host \"MediaTools backend already running on port 7860. PID=$pid\"; Set-Content -LiteralPath $pidFile -Value $pid -Encoding ascii; exit 10 }; Write-Host \"Port 7860 is already used by another process. PID=$pid\"; exit 20 } }; exit 0"
if "%ERRORLEVEL%"=="10" goto OPEN_BROWSER
if "%ERRORLEVEL%"=="20" goto PORT_BUSY
if errorlevel 1 goto FAILED

echo [2/3] Launching backend in background...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '.').Path; $pidFile=Join-Path $root '%PID_FILE%'; $logFile=Join-Path $root '%LOG_FILE%'; $errFile=Join-Path $root '%ERR_FILE%'; Remove-Item -LiteralPath $logFile -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue; $proc=Start-Process -FilePath 'python' -ArgumentList 'app.py' -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errFile; Start-Sleep -Seconds 2; if ($proc.HasExited) { Write-Host \"MediaTools backend failed to start. ExitCode=$($proc.ExitCode). See %ERR_FILE%\"; exit 1 }; Set-Content -LiteralPath $pidFile -Value $proc.Id -Encoding ascii; Write-Host \"MediaTools backend started. PID=$($proc.Id)\""
if errorlevel 1 goto FAILED

:OPEN_BROWSER
echo [3/3] Opening WebUI...
start "" "%URL%"

echo.
echo MediaTools WebUI is starting at %URL%
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
