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
$physicalImage = 'ghcr.io/librelane/librelane@sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
& docker volume inspect $PdkVolume --format '{{.Name}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "The native STA replay needs the existing pinned PDK volume $PdkVolume." }
New-Item -ItemType Directory -Path $scratch | Out-Null
$common = @(
    'run', '--rm', '--network', 'none', '--read-only',
    '--mount', "type=bind,source=$checkout,target=/work,readonly",
    '--mount', "type=bind,source=$PSScriptRoot,target=/council,readonly",
    '--mount', "type=volume,source=$PdkVolume,target=/pdk,readonly",
    '--workdir', '/work', '--entrypoint', 'python3', $physicalImage, '-B'
)
$probes = [ordered]@{
    'signoff_audit'='signoff-audit'
    'contact_audit'='contact-audit'
    'sta_sensitivity'='sta-sensitivity'
    'sta_sync'='sta-sync'
}
foreach ($source in $probes.GetEnumerator()) {
    $name = $source.Value + '.json'
    $fresh = Join-Path $scratch $name
    $reference = Join-Path (Join-Path $PSScriptRoot 'results') $name
    $observed = & docker @common "/council/sources/$($source.Key).py"
    if ($LASTEXITCODE -ne 0) { throw "The $($source.Key) native replay failed." }
    $observed | Set-Content -Encoding utf8NoBOM -LiteralPath $fresh
    & python -B -c 'import json,sys; from pathlib import Path; a,b=(json.loads(Path(p).read_bytes()) for p in sys.argv[1:]); sys.exit(0 if a==b else 1)' $fresh $reference
    if ($LASTEXITCODE -ne 0) { throw "The $name results differ from the council record." }
    Write-Output "$name matched the retained observations"
}
