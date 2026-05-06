# MediaTools 依赖更新脚本 (Windows PowerShell)
# 用法: .\scripts\update.ps1

$Root = Split-Path $PSScriptRoot -Parent
Write-Host "=== MediaTools 依赖更新 ===" -ForegroundColor Cyan

# 1. 更新 yt-dlp 二进制
Write-Host "`n[1/2] 更新 yt-dlp..." -ForegroundColor Yellow
$ytdlpBin = Join-Path $Root "bin\yt-dlp.exe"
if (Test-Path $ytdlpBin) {
    & $ytdlpBin -U
} else {
    Write-Host "  yt-dlp.exe 未找到，正在下载最新版本..."
    $url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    Invoke-WebRequest -Uri $url -OutFile $ytdlpBin
    Write-Host "  yt-dlp.exe 下载完成"
}

# 2. 更新 unlock-music（手动操作提示）
Write-Host "`n[2/2] unlock-music 更新提示..." -ForegroundColor Yellow
Write-Host "  unlock-music 是手动复制的源码，请前往以下地址获取最新版："
Write-Host "  https://git.um-react.app/um/cli"
Write-Host "  下载后运行 .\scripts\build-um.ps1 重新编译"

Write-Host "`n=== 更新完成 ===" -ForegroundColor Green
