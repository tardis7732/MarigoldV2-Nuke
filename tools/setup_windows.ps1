# Install an isolated Windows CUDA engine, download normals assets, and configure the launcher.
param([string]$Repository = '', [switch]$SkipDownload)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$enginePython = Join-Path $projectRoot '.venv-engine/Scripts/python.exe'
if (-not $Repository) { $Repository = Join-Path $projectRoot 'engine/marigold-v2' }
$revision = '18466672fb8661152434a0efe1184939164cda19'

function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed with exit code $LASTEXITCODE" }
}

if (-not (Test-Path -LiteralPath $Repository)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $Repository) -Force | Out-Null
    Invoke-Checked git @('clone', 'https://github.com/huawei-bayerlab/marigold-v2.git', $Repository)
    Invoke-Checked git @('-C', $Repository, 'checkout', $revision)
}
$actual = (& git -C $Repository rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actual -ne $revision) { throw 'Repository revision differs from the adapter pin. Use a fresh directory.' }
if (-not (Test-Path -LiteralPath $enginePython)) {
    Invoke-Checked uv @('venv', '--python', '3.10', (Join-Path $projectRoot '.venv-engine'))
}
Invoke-Checked uv @('pip', 'install', '--python', $enginePython, 'torch==2.10.0', 'torchvision==0.25.0', '--index-url', 'https://download.pytorch.org/whl/cu128')
Invoke-Checked uv @('pip', 'install', '--python', $enginePython, '-e', $Repository)
Invoke-Checked uv @('pip', 'check', '--python', $enginePython)
Invoke-Checked $enginePython @('-c', 'import torch; assert torch.cuda.is_available(), "CUDA unavailable"; print(torch.__version__, torch.cuda.get_device_name())')
$assets = Join-Path $projectRoot 'assets'
if (-not $SkipDownload) {
    Invoke-Checked $enginePython @((Join-Path $PSScriptRoot 'download_normals.py'), '--assets', $assets)
}
Invoke-Checked $enginePython @((Join-Path $PSScriptRoot 'configure_engine.py'), '--python', $enginePython, '--repo', $Repository, '--assets', $assets)
Write-Host 'Engine configured. In Nuke: Engine > Start, then clear the selected node cache.'
Write-Host 'First inference loads and quantizes the model; see output/daemon.log.'
