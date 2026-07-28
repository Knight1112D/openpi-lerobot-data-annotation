param(
    [switch] $Online
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Uv = Join-Path $ProjectRoot "uv.exe"
$PythonInstaller = Join-Path $ProjectRoot "packages\python-3.11.9-amd64.exe"
$PythonRoot = Join-Path $ProjectRoot ".runtime\python"
$Python = Join-Path $PythonRoot "python.exe"
$WheelDir = Join-Path $ProjectRoot "packages\wheels"

if (-not (Test-Path -LiteralPath $Uv)) {
    $UvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $UvCommand) {
        throw "找不到 uv.exe。请把完整部署包解压后运行，或先安装 uv。"
    }
    $Uv = $UvCommand.Source
}

New-Item -ItemType Directory -Force $PythonRoot | Out-Null
if (-not (Test-Path -LiteralPath $Python)) {
    if (Test-Path -LiteralPath $PythonInstaller) {
        Write-Host "安装项目内 Python 3.11..."
        $InstallerArgs = @(
            "/quiet",
            "InstallAllUsers=0",
            "PrependPath=0",
            "Include_test=0",
            "TargetDir=$PythonRoot"
        )
        $process = Start-Process -FilePath $PythonInstaller -ArgumentList $InstallerArgs -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "Python 安装失败，退出码：$($process.ExitCode)"
        }
    } else {
        Write-Host "部署包没有 Python 安装包，使用 uv 在线安装 Python 3.11..."
        & $Uv python install 3.11
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (& $Uv python find 3.11).Trim()
}

$SyncArgs = @("sync", "--python", $Python)
if (-not $Online -and (Test-Path -LiteralPath $WheelDir)) {
    Write-Host "使用本地 wheel 离线安装依赖..."
    $SyncArgs += @("--offline", "--find-links", $WheelDir)
} else {
    Write-Host "使用网络安装依赖..."
}
& $Uv @SyncArgs

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "uv 环境创建失败：$VenvPython"
}
& $VenvPython (Join-Path $ProjectRoot "scripts\data_annotation.py") --help
Write-Host "部署完成。后续请使用 .\scripts\run.ps1 template/validate/propagate。"
