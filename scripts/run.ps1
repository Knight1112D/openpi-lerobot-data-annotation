param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Arguments
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Entrypoint = Join-Path $ProjectRoot "scripts\data_annotation.py"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error "项目环境不存在：$Python；请先运行 uv sync --python 3.11"
    exit 1
}

& $Python $Entrypoint @Arguments
exit $LASTEXITCODE
