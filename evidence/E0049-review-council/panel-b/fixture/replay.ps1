param(
    [Parameter(Mandatory = $true)]
    [string]$ScratchRoot,
    [string]$PdkVolume = 'protocol-emulator-g1-pdk-89d42ee6'
)
$ErrorActionPreference = 'Stop'
$checkout = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Run this script from its retained location in the checkout.' }
$scratch = [IO.Path]::GetFullPath($ScratchRoot)
if ([IO.Path]::GetPathRoot($scratch) -ine 'H:\') { throw 'The council stores experimental output on H:.' }
if (Test-Path -LiteralPath $scratch) { throw "Choose a fresh result directory. $scratch already exists." }
& docker volume inspect $PdkVolume --format '{{.Name}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Mount the pinned 89d42ee6 PDK volume for its three functional cell models.' }
New-Item -ItemType Directory -Path $scratch | Out-Null
$temporary = New-Item -ItemType Directory -Path (Join-Path $scratch 'tmp')
$common = @(
    'run', '--rm', '--network', 'none', '--read-only',
    '--mount', "type=bind,source=$checkout,target=/work,readonly",
    '--mount', "type=bind,source=$PSScriptRoot,target=/record,readonly",
    '--mount', "type=bind,source=$($temporary.FullName),target=/tmp",
    '--mount', "type=volume,source=$PdkVolume,target=/pdk,readonly",
    '--workdir', '/work', 'protocol-emulator-asic-workbench:2026-07-29', 'python3', '-B'
)
$probes = [ordered]@{'fixture_sensitivity'='fixture-sensitivity';'switch_reselect'='switch-reselect'}
foreach ($probe in $probes.GetEnumerator()) {
    $name = $probe.Value + '.json'
    $fresh = Join-Path $scratch $name
    $expected = Join-Path (Join-Path $PSScriptRoot 'results') $name
    $observed = & docker @common "/record/$($probe.Key).py"
    if ($LASTEXITCODE -ne 0) { throw "The $($probe.Key) experiment failed." }
    $observed | Set-Content -Encoding utf8NoBOM -LiteralPath $fresh
    & python -B -c 'import json,sys; from pathlib import Path; a,b=(json.loads(Path(p).read_bytes()) for p in sys.argv[1:]); sys.exit(0 if a==b else 1)' $fresh $expected
    if ($LASTEXITCODE -ne 0) { throw "$name differed from the retained observations." }
    Write-Output "$name matched the retained result"
}
