param(
    [Parameter(Mandatory = $true)]
    [string]$ScratchRoot
)
$ErrorActionPreference = 'Stop'
$checkout = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Run this script from its retained location in the checkout.' }
$scratch = [IO.Path]::GetFullPath($ScratchRoot)
if ([IO.Path]::GetPathRoot($scratch) -ine 'H:\') { throw 'The council stores experimental output on H:.' }
if (Test-Path -LiteralPath $scratch) { throw "Choose a fresh result directory. $scratch already exists." }
New-Item -ItemType Directory -Path $scratch | Out-Null
$temporary = New-Item -ItemType Directory -Path (Join-Path $scratch 'tmp')
$imageName = 'protocol-emulator-asic-workbench:2026-07-29'
$container = @(
    'run', '--rm', '--network', 'none', '--read-only',
    '--mount', "type=bind,source=$checkout,target=/work,readonly",
    '--mount', "type=bind,source=$PSScriptRoot,target=/council,readonly",
    '--mount', "type=bind,source=$scratch,target=/results",
    '--mount', "type=bind,source=$($temporary.FullName),target=/tmp",
    '--workdir', '/work', '-e', 'PYTHONDONTWRITEBYTECODE=1',
    '-e', 'PROTOCOL_EMULATOR_LOCKED_WORKBENCH=1', $imageName
)
$paths = & docker @container python3 /council/sources/inspect_retained.py
if ($LASTEXITCODE -ne 0) { throw 'The retained G4 inspection failed.' }
$paths | Set-Content -Encoding utf8NoBOM -LiteralPath (Join-Path $scratch 'retained-paths.json')
foreach ($probe in 'launch', 'guard', 'retime') {
    $module = @{launch='run_launch'; guard='guard_screen'; retime='retime_screen'}[$probe]
    & docker @container python3 "/council/sources/$module.py" --root /work --out "/results/$probe"
    if ($LASTEXITCODE -ne 0) { throw "$probe failed. Its log and any preliminary observations are in $scratch." }
}
& docker @container python3 /council/sources/verify_replay.py /council/results /results
if ($LASTEXITCODE -ne 0) { throw 'The fresh observations differed from the council records.' }
