# MediaTools development startup helpers

<#
.SYNOPSIS
Stop processes by port number.
#>
function Stop-ProcessByPort {
    param(
        [int[]]$Ports
    )

    try {
        $connections = Get-NetTCPConnection -LocalPort $Ports -ErrorAction SilentlyContinue
        if ($connections) {
            $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($processId in $pids) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        }
    }
    catch {
        # Ignore errors and continue.
    }
}

<#
.SYNOPSIS
Wait for a port to become ready.
#>
function Wait-ForPort {
    param(
        [int]$Port,
        [int]$MaxWaitSeconds = 10
    )

    $startTime = Get-Date
    $maxWait = [timespan]::FromSeconds($MaxWaitSeconds)

    while ((Get-Date) - $startTime -lt $maxWait) {
        try {
            $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            if ($conn) {
                return $true
            }
        }
        catch {
            # Keep polling until timeout.
        }

        Start-Sleep -Milliseconds 500
    }

    return $false
}

<#
.SYNOPSIS
Get the listener PID for a local port.
#>
function Get-ListeningProcessId {
    param(
        [int]$Port
    )

    $listenerPids = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    if ($listenerPids.Count -gt 0) {
        return $listenerPids[0]
    }

    return $null
}

<#
.SYNOPSIS
Start backend and Vite in parallel and wait for both ports.
#>
function Start-BackendAndVite {
    param(
        [string]$RootDir,
        [string]$FrontendDir,
        [string]$ViteUrl,
        [string]$LogFile,
        [string]$ErrFile,
        [string]$ViteLogFile,
        [string]$ViteErrFile,
        [string]$PidFile,
        [string]$VitePidFile
    )

    # Start backend.
    $env:MEDIATOOLS_FRONTEND_DEV_URL = $ViteUrl
    $env:LOG_MODE = 'development'

    $backendProc = Start-Process -FilePath 'python' `
        -ArgumentList 'app.py', '--reload' `
        -WorkingDirectory $RootDir `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $ErrFile

    # Start Vite.
    $viteProc = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort' `
        -WorkingDirectory $FrontendDir `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $ViteLogFile `
        -RedirectStandardError $ViteErrFile

    # Wait for both ports to come up.
    $backendReady = $false
    $viteReady = $false
    $maxWait = 15
    $elapsed = 0

    while ($elapsed -lt $maxWait -and (-not $backendReady -or -not $viteReady)) {
        if (-not $backendReady) {
            $backendReady = Wait-ForPort -Port 7860 -MaxWaitSeconds 1
        }

        if (-not $viteReady) {
            $viteReady = Wait-ForPort -Port 5173 -MaxWaitSeconds 1
        }

        $elapsed += 1

        # Stop early if either process exits before its port is ready.
        if ($backendProc.HasExited -and -not $backendReady) {
            Write-Host "Backend failed to start. See $ErrFile"
            return $false
        }

        if ($viteProc.HasExited -and -not $viteReady) {
            Write-Host "Vite failed to start. See $ViteErrFile"
            return $false
        }
    }

    if (-not $backendReady -or -not $viteReady) {
        Write-Host "Startup timeout: Backend=$backendReady, Vite=$viteReady"
        return $false
    }

    $viteListenerPid = Get-ListeningProcessId -Port 5173
    if (-not $viteListenerPid) {
        $viteListenerPid = $viteProc.Id
    }

    # Persist PIDs for cleanup.
    Set-Content -LiteralPath $PidFile -Value $backendProc.Id -Encoding ascii
    Set-Content -LiteralPath $VitePidFile -Value $viteListenerPid -Encoding ascii

    Write-Host "Backend started. PID=$($backendProc.Id)"
    Write-Host "Vite started. PID=$viteListenerPid"

    return $true
}

<#
.SYNOPSIS
Check whether the MediaTools backend is already listening on a port.
#>
function Test-ExistingMediaToolsBackend {
    param(
        [string]$PidFile,
        [int]$Port = 7860
    )

    $listenerPids = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    if ($listenerPids.Count -eq 0) {
        return 0
    }

    foreach ($listenerPid in $listenerPids) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$listenerPid" -ErrorAction SilentlyContinue
        if ($proc -and $proc.Name -match '^python' -and $proc.CommandLine -like '*app.py*') {
            Write-Host "MediaTools backend already running on port $Port. PID=$listenerPid"
            Set-Content -LiteralPath $PidFile -Value $listenerPid -Encoding ascii
            return 10
        }
    }

    Write-Host "Port $Port is already used by another process. PID=$($listenerPids[0])"
    return 20
}

<#
.SYNOPSIS
Run one backend watchdog cycle for the production startup script.
#>
function Invoke-MediaToolsBackendWatchdogCycle {
    param(
        [string]$RootDir,
        [string]$PidFile,
        [string]$LogFile,
        [string]$ErrFile,
        [string]$Url,
        [bool]$OpenBrowser = $false
    )

    Remove-Item -LiteralPath $LogFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ErrFile -Force -ErrorAction SilentlyContinue

    # 生产模式必须走 frontend/dist；若残留开发代理变量，静态站点会变成 502。
    Remove-Item Env:\MEDIATOOLS_FRONTEND_DEV_URL -ErrorAction SilentlyContinue
    $env:LOG_MODE = 'production'

    $proc = Start-Process -FilePath 'python' `
        -ArgumentList 'app.py' `
        -WorkingDirectory $RootDir `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $ErrFile

    Set-Content -LiteralPath $PidFile -Value $proc.Id -Encoding ascii
    Write-Host "MediaTools backend started. PID=$($proc.Id)"

    Start-Sleep -Seconds 2

    if ($proc.HasExited) {
        Write-Host "MediaTools backend failed to start. ExitCode=$($proc.ExitCode). See $ErrFile"
        return 1
    }

    if ($OpenBrowser) {
        Write-Host '[3/4] Opening WebUI...'
        Start-Process $Url
    }

    $proc.WaitForExit()
    return $proc.ExitCode
}
