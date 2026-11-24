# Reproduce the production checks without writing to the source checkout.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]*$')][string]$RunName,
    [string]$Image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
if ([IO.Path]::GetPathRoot($repo) -ne 'H:\') { throw 'Use the H: checkout for this council replay.' }
$run = Join-Path $repo "build/council-2026-11-24/chair/validation/$RunName"
if (Test-Path -LiteralPath $run) { throw "Select a new run name. The existing run is at $run" }
$build = (New-Item -Type Directory -Path (Join-Path $run 'build') -Force).FullName
$testCopy = (New-Item -Type Directory -Path (Join-Path $run 'test')).FullName

# The stock smoke target writes test/tb-gl-harness.fst. Give it its own test sources.
$sourceFiles = @(git -C $repo ls-files -- test)
if ($LASTEXITCODE -ne 0 -or $sourceFiles.Count -eq 0) { throw 'Could not identify the tracked test sources.' }
foreach ($name in $sourceFiles) {
    $source = Join-Path $repo $name
    $target = Join-Path $testCopy $name.Substring('test/'.Length)
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target
    if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash) {
        throw "Test source copy differs at $name"
    }
}

# FST uses mmap on anonymous temporary files. Its transient /tmp needs Linux semantics.
$containerArgs = @('run', '--rm', '--pull=never', '--init', '--network', 'none', '--read-only',
    '--ulimit', 'core=0:0', '--tmpfs', '/tmp:rw,mode=1777,size=32m',
    '--mount', "type=bind,source=$repo,target=/workspace,readonly",
    '--mount', "type=bind,source=$build,target=/workspace/build",
    '--mount', "type=bind,source=$testCopy,target=/workspace/test", '-w', '/workspace',
    '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'GIT_CONFIG_COUNT=1',
    '-e', 'GIT_CONFIG_KEY_0=safe.directory', '-e', 'GIT_CONFIG_VALUE_0=/workspace',
    $Image, 'make', 'CURRENT_ARTIFACTS=/workspace/build/current', 'doctor', 'check', 'test')
docker @containerArgs
if ($LASTEXITCODE -ne 0) { throw "Production checks failed. Inspect $build/current/runs" }
Write-Output "Production receipts and provenance are in $build/current"
