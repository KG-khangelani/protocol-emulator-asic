param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_-]*$')]
    [string]$RunName,
    [string]$PdkVolume = 'protocol-emulator-g1-pdk-89d42ee6'
)
$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$driver = 'evidence/E0049-review-council/uart-ablation'
if (-not (Test-Path -LiteralPath "$repo/$driver/map_variant.py")) {
    throw 'Run this from the repository root.'
}
$relative = "build/$RunName"
$scratch = Join-Path $repo $relative
if (Test-Path -LiteralPath $scratch) { throw "Use a fresh build name: $RunName" }
$null = New-Item -ItemType Directory -Path $scratch
$tempDir = (New-Item -ItemType Directory -Path (Join-Path $scratch 'tmp')).FullName
$repoMount = "type=bind,source=$repo,target=/work,readonly"
$scratchMount = "type=bind,source=$scratch,target=/work/$relative"
$tempMount = "type=bind,source=$tempDir,target=/tmp"
$pdkMount = "type=volume,source=$PdkVolume,target=/pdk,readonly"
$workbench = 'protocol-emulator-asic-workbench:2026-07-29'
$physical = 'ghcr.io/librelane/librelane@sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
$common = @('run', '--rm', '--pull=never', '--network', 'none', '--init', '--read-only',
    '--mount', $repoMount, '--mount', $scratchMount, '--mount', $tempMount,
    '-w', '/work', '-e', 'PYTHONDONTWRITEBYTECODE=1')
docker volume inspect --format '{{.Name}}' $PdkVolume
if ($LASTEXITCODE) { throw 'Mount the existing pinned CMOS5L PDK for this replay.' }
docker @common $workbench python3 -B "$driver/map_variant.py" prepare "$relative/mapped"
if ($LASTEXITCODE) { throw 'Preparing the isolated reference and variant failed.' }
docker @common --mount $pdkMount --entrypoint python3 $physical -B "$driver/map_variant.py" map "$relative/mapped"
if ($LASTEXITCODE) { throw 'Matched nominal synthesis failed.' }
docker @common $workbench python3 -B "$driver/check_variant.py" "$relative/mapped" "$relative/functional"
if ($LASTEXITCODE) { throw 'The candidate public-pin checks failed.' }
Write-Output "Results are in $scratch."
