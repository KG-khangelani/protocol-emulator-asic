[CmdletBinding()]
param(
    [ValidateSet('Setup', 'Build', 'Doctor', 'Check', 'Lint', 'Test', 'TestVerilator', 'Formal', 'Synth', 'Evidence', 'LearnStatus', 'LearnM0', 'LearnWaveform', 'All', 'Shell')]
    [string]$Command = 'All',
    [ValidateSet('All', 'RTL', 'Verification', 'Physical', 'Claims')]
    [string]$Section = 'All'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$image = 'protocol-emulator-asic-workbench:2026-07-29'
$dockerfile = Join-Path $repoRoot 'tools\workbench\Dockerfile'
$context = Join-Path $repoRoot 'tools\workbench'

# The two read-only lessons inspect committed text evidence and use only the
# Python standard library. Prefer a working host Python so a Docker outage does
# not block the learning half of the project. All EDA execution remains in the
# locked container below; if Python is unavailable, these commands retain the
# container fallback.
if ($Command -in @('LearnStatus', 'LearnM0')) {
    $hostPython = $null
    foreach ($candidate in @(Get-Command python -CommandType Application -All -ErrorAction SilentlyContinue)) {
        & $candidate.Source --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $hostPython = $candidate
            break
        }
    }
    if ($null -ne $hostPython) {
        $lessonArguments = @()
        if ($Command -eq 'LearnStatus') {
            $lessonArguments += (Join-Path $repoRoot 'tools\learning_status.py')
        }
        else {
            $lessonArguments += @(
                (Join-Path $repoRoot 'tools\m0_walkthrough.py'),
                '--section',
                $Section.ToLowerInvariant()
            )
        }
        Write-Output 'HOST LEARNING MODE: read-only evidence lesson; Docker and EDA tools are not required.'
        & $hostPython.Source @lessonArguments
        if ($LASTEXITCODE -ne 0) {
            throw "host Python lesson exited with status $LASTEXITCODE"
        }
        exit 0
    }
    Write-Output 'Host Python is unavailable; using the locked Docker fallback for this lesson.'
}

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
    'LearnStatus' { @('make', 'learn-status') }
    'LearnM0'  { @('python3', 'tools/m0_walkthrough.py', '--section', $Section.ToLowerInvariant()) }
    'LearnWaveform' { @('make', 'learn-waveform') }
    'All'      { @('make', 'doctor', 'check', 'lint', 'test', 'test-verilator', 'formal', 'synth') }
    'Shell'    { @('bash') }
}

$mount = "type=bind,source=$repoRoot,target=/workspace"
$arguments = @('run', '--rm', '--init', '--mount', $mount, '--workdir', '/workspace', $image) + $inside
Invoke-CheckedDocker -Arguments $arguments
