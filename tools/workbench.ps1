[CmdletBinding()]
param(
    [ValidateSet('Setup', 'Build', 'Doctor', 'Check', 'Lint', 'Test', 'TestVerilator', 'Formal', 'Synth', 'Evidence', 'LearnM0', 'LearnWaveform', 'All', 'Shell')]
    [string]$Command = 'All',
    [ValidateSet('All', 'RTL', 'Verification', 'Physical', 'Claims')]
    [string]$Section = 'All'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$image = 'protocol-emulator-asic-workbench:2026-07-29'
$dockerfile = Join-Path $repoRoot 'tools\workbench\Dockerfile'
$context = Join-Path $repoRoot 'tools\workbench'

function Invoke-CheckedDocker {
    param([string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker exited with status $LASTEXITCODE"
    }
}

function Build-Workbench {
    Invoke-CheckedDocker -Arguments @('build', '--file', $dockerfile, '--tag', $image, $context)
}

if ($Command -in @('Setup', 'Build')) {
    Build-Workbench
    exit 0
}

& docker image inspect $image *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Workbench image is absent; building $image"
    Build-Workbench
}

$inside = switch ($Command) {
    'Doctor'   { @('make', 'doctor') }
    'Check'    { @('make', 'check') }
    'Lint'     { @('make', 'lint') }
    'Test'     { @('make', 'test') }
    'TestVerilator' { @('make', 'test-verilator') }
    'Formal'   { @('make', 'formal') }
    'Synth'    { @('make', 'synth') }
    'Evidence' { @('make', 'evidence') }
    'LearnM0'  { @('python3', 'tools/m0_walkthrough.py', '--section', $Section.ToLowerInvariant()) }
    'LearnWaveform' { @('make', 'learn-waveform') }
    'All'      { @('make', 'doctor', 'check', 'lint', 'test', 'test-verilator', 'formal', 'synth') }
    'Shell'    { @('bash') }
}

$mount = "type=bind,source=$repoRoot,target=/workspace"
$arguments = @('run', '--rm', '--init', '--mount', $mount, '--workdir', '/workspace', $image) + $inside
Invoke-CheckedDocker -Arguments $arguments
