param([string]$Python = 'python', [switch]$SkipBuild, [string]$BuildDirectory = 'build')
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
if (-not $SkipBuild) {
    & (Join-Path $projectRoot 'ofx/build.ps1') -BuildDirectory $BuildDirectory
    if ($LASTEXITCODE) { throw 'OFX build failed' }
}
$pythonPath = (& $Python -c 'import sys; print(sys.executable)').Trim()
if ($LASTEXITCODE -or -not (Test-Path -LiteralPath $pythonPath)) { throw 'External Python not found' }
$buildRoot = Join-Path (Join-Path $projectRoot 'ofx') $BuildDirectory
$bundle = Join-Path $buildRoot 'MarigoldV2Normals.ofx.bundle/Contents/Win64'
if (-not (Test-Path -LiteralPath (Join-Path $bundle 'MarigoldV2Normals.ofx'))) { throw 'Build the OFX first' }
$utf8 = New-Object System.Text.UTF8Encoding($false)
$configText = "root=$($projectRoot.Replace('\','/'))`npython=$($pythonPath.Replace('\','/'))`ndaemon=$($projectRoot.Replace('\','/'))/daemon/launcher.py`nport=47822`n"
[IO.File]::WriteAllText((Join-Path $bundle 'marigoldv2.cfg'), $configText, $utf8)
[IO.File]::WriteAllText((Join-Path $projectRoot 'config/frontend.json'), (@{python=$pythonPath; ofx_build_dir=$buildRoot} | ConvertTo-Json), $utf8)
$nukeDir = Join-Path $env:USERPROFILE '.nuke'
New-Item -ItemType Directory -Path $nukeDir -Force | Out-Null
$init = Join-Path $nukeDir 'init.py'
$nukePluginPath = (Join-Path $projectRoot 'nuke').Replace('\','/')
$pathLiteral = ConvertTo-Json -InputObject $nukePluginPath -Compress
$line = "nuke.pluginAddPath($pathLiteral)"
$existing = if (Test-Path -LiteralPath $init) { [IO.File]::ReadAllText($init) } else { '' }
if (-not $existing.Contains($line)) {
    if (Test-Path -LiteralPath $init) {
        Copy-Item -LiteralPath $init -Destination "$init.marigold-backup-$(Get-Date -Format yyyyMMddHHmmss)"
    }
    [IO.File]::WriteAllText($init, $existing + "`n# Marigold V2 Normals`nimport nuke`n$line`n", $utf8)
}
Write-Host 'Nuke menu registered. Restart Nuke, then Nodes > ML > Marigold V2 > Marigold V2.'
Write-Host 'Configure the CUDA engine with tools/configure_engine.py before rendering.'
