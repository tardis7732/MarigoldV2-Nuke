# Build the MarigoldV2Normals OFX plugin with the MSVC toolset.
#
#   powershell -ExecutionPolicy Bypass -File ofx\build.ps1 [-Config Release]
#
# Needs Visual Studio 2022 (any edition, or Build Tools) with the
# "Desktop development with C++" workload. Uses the CMake + Ninja that ship
# with it, or cmake/ninja on PATH. Output:
#   ofx\build\MarigoldV2Normals.ofx.bundle\Contents\Win64\MarigoldV2Normals.ofx
# install.ps1 at the repo root copies it into the OFX plugin directory.
param(
    [string]$Config = "Release"
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-VS {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $p = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null
        if ($p) { return $p.Trim() }
    }
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        foreach ($year in @("2022", "2019")) {
            foreach ($ed in @("Community", "Professional", "Enterprise", "BuildTools")) {
                $cand = Join-Path $base "Microsoft Visual Studio\$year\$ed"
                if (Test-Path (Join-Path $cand "VC\Auxiliary\Build\vcvars64.bat")) { return $cand }
            }
        }
    }
    return $null
}

$vs = Find-VS
if (-not $vs) { throw "Visual Studio with C++ tools not found. Install VS 2022 Build Tools with the C++ workload." }
$vcvars = Join-Path $vs "VC\Auxiliary\Build\vcvars64.bat"
$cmake = Join-Path $vs "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
$ninja = Join-Path $vs "Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
if (-not (Test-Path $cmake)) { $cmake = "cmake" }
if (-not (Test-Path $ninja)) { $ninja = "ninja" }

$build = Join-Path $here "build"
$script = @"
@echo off
call "$vcvars" >nul
set VSLANG=1033
"$cmake" -S "$here" -B "$build" -G Ninja -DCMAKE_MAKE_PROGRAM="$ninja" -DCMAKE_BUILD_TYPE=$Config || exit /b 1
"$cmake" --build "$build" || exit /b 1
"@
$bat = Join-Path $env:TEMP "marigoldv2_ofx_build.cmd"
Set-Content -Path $bat -Value $script -Encoding ASCII
& cmd.exe /c $bat
if ($LASTEXITCODE) { throw "build failed" }
Write-Host "built: $build\MarigoldV2Normals.ofx.bundle\Contents\Win64\MarigoldV2Normals.ofx"
