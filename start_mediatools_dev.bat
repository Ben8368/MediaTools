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
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '.').Path; $frontend=Join-Path $root 'frontend'; try { $backendPids=@(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); $vitePids=@(Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); $targets=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { (($_.Name -eq 'python.exe') -or ($_.Name -eq 'pythonw.exe') -or ($_.Name -eq 'node.exe') -or ($_.Name -eq 'cmd.exe')) -and (($_.CommandLine -like \"*$root*app.py*\") -or ($_.CommandLine -like \"*$root*api_server*\") -or ($_.CommandLine -like \"*$frontend*\" -and $_.CommandLine -like '*vite*') -or (($vitePids -contains $_.ProcessId) -and ($_.Name -eq 'node.exe') -and ($_.CommandLine -like '*vite*')) -or (($backendPids -contains $_.ProcessId) -and (($_.Name -eq 'python.exe') -or ($_.Name -eq 'pythonw.exe')) -and ($_.CommandLine -like '*app.py*'))) }); if ($targets.Count -gt 0) { $targets | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } } } catch { Write-Host \"Warning: could not stop existing dev processes: $($_.Exception.Message)\" }; Remove-Item -LiteralPath (Join-Path $root '%PID_FILE%') -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath (Join-Path $root '%VITE_PID_FILE%') -Force -ErrorAction SilentlyContinue; exit 0"
if errorlevel 1 goto FAILED

echo [2/4] Launching backend with reload...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '.').Path; $env:MEDIATOOLS_FRONTEND_DEV_URL='%VITE_URL%'; $env:LOG_MODE='development'; $pidFile=Join-Path $root '%PID_FILE%'; $logFile=Join-Path $root '%LOG_FILE%'; $errFile=Join-Path $root '%ERR_FILE%'; $proc=Start-Process -FilePath 'python' -ArgumentList 'app.py','--reload' -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errFile; Start-Sleep -Seconds 4; $backendCandidates=@(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Get-CimInstance Win32_Process -Filter \"ProcessId=$_\" -ErrorAction SilentlyContinue } | Where-Object { $_ -and ($_.Name -match '^python') -and ($_.CommandLine -like '*app.py*') }); if ($proc.HasExited -and $backendCandidates.Count -eq 0) { Write-Host \"Backend failed to start. See %ERR_FILE%\"; exit 1 }; $backendPid=if ($backendCandidates.Count -gt 0) { $backendCandidates[0].ProcessId } else { $proc.Id }; Set-Content -LiteralPath $pidFile -Value $backendPid -Encoding ascii; Write-Host \"Backend started. PID=$backendPid\""
if errorlevel 1 goto FAILED

echo [3/4] Launching Vite dev server...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '.').Path; $frontend=Join-Path $root 'frontend'; $pidFile=Join-Path $root '%VITE_PID_FILE%'; $logFile=Join-Path $root '%VITE_LOG_FILE%'; $errFile=Join-Path $root '%VITE_ERR_FILE%'; $proc=Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm run dev -- --host 127.0.0.1 --port 5173 --strictPort' -WorkingDirectory $frontend -PassThru -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errFile; Start-Sleep -Seconds 3; if ($proc.HasExited) { Write-Host \"Vite failed to start. See %VITE_ERR_FILE%\"; exit 1 }; Set-Content -LiteralPath $pidFile -Value $proc.Id -Encoding ascii; Write-Host \"Vite started. PID=$($proc.Id)\""
if errorlevel 1 goto FAILED

echo [4/4] Opening MediaTools...
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
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '.').Path; $frontend=Join-Path $root 'frontend'; try { $backendPids=@(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); $vitePids=@(Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); $targets=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { (($_.Name -eq 'python.exe') -or ($_.Name -eq 'pythonw.exe') -or ($_.Name -eq 'node.exe') -or ($_.Name -eq 'cmd.exe')) -and (($_.CommandLine -like \"*$root*app.py*\") -or ($_.CommandLine -like \"*$root*api_server*\") -or ($_.CommandLine -like \"*$frontend*\" -and $_.CommandLine -like '*vite*') -or (($vitePids -contains $_.ProcessId) -and ($_.Name -eq 'node.exe') -and ($_.CommandLine -like '*vite*')) -or (($backendPids -contains $_.ProcessId) -and (($_.Name -eq 'python.exe') -or ($_.Name -eq 'pythonw.exe')) -and ($_.CommandLine -like '*app.py*'))) }); if ($targets.Count -gt 0) { $targets | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } } } catch { }"
exit /b 0

:FAILED
echo.
echo MediaTools dev mode failed to start.
pause
exit /b 1
