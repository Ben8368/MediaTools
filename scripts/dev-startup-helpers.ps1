# MediaTools 开发模式启动辅助函数

<#
.SYNOPSIS
通过端口号快速终止进程
#>
function Stop-ProcessByPort {
    param(
        [int[]]$Ports
    )

    try {
        $connections = Get-NetTCPConnection -LocalPort $Ports -ErrorAction SilentlyContinue
        if ($connections) {
            $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($pid in $pids) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
    }
    catch {
        # 忽略错误，继续执行
    }
}

<#
.SYNOPSIS
智能等待端口就绪
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
            # 继续轮询
        }

        Start-Sleep -Milliseconds 500
    }

    return $false
}

<#
.SYNOPSIS
并行启动后端和 Vite，并等待两个端口都就绪
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

    # 启动后端
    $env:MEDIATOOLS_FRONTEND_DEV_URL = $ViteUrl
    $env:LOG_MODE = 'development'

    $backendProc = Start-Process -FilePath 'python' `
        -ArgumentList 'app.py', '--reload' `
        -WorkingDirectory $RootDir `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $ErrFile

    # 启动 Vite
    $viteProc = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort' `
        -WorkingDirectory $FrontendDir `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $ViteLogFile `
        -RedirectStandardError $ViteErrFile

    # 并行等待两个端口就绪
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

        # 检查进程是否已退出
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

    # 保存 PID
    Set-Content -LiteralPath $PidFile -Value $backendProc.Id -Encoding ascii
    Set-Content -LiteralPath $VitePidFile -Value $viteProc.Id -Encoding ascii

    Write-Host "Backend started. PID=$($backendProc.Id)"
    Write-Host "Vite started. PID=$($viteProc.Id)"

    return $true
}
