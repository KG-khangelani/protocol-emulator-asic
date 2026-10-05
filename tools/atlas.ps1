[CmdletBinding()]
param(
    [ValidateSet('Start', 'Build', 'Check')]
    [string]$Action = 'Start'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$atlasDirectory = Join-Path $PSScriptRoot '..\web'
$npmCommand = (Get-Command npm.cmd -ErrorAction Stop).Source
$nodeVersion = [version]((& node --version).Trim().TrimStart('v'))
if ($LASTEXITCODE -ne 0 -or $nodeVersion.Major -lt 24) {
    throw 'Protocol atlas requires Node 24 or newer. No global install or security change is performed.'
}
if (-not (Test-Path (Join-Path $atlasDirectory 'node_modules'))) {
    throw 'Project dependencies are absent. Run npm ci --ignore-scripts from web, then retry.'
}

Push-Location $atlasDirectory
try {
    if ($Action -eq 'Check') {
        & $npmCommand test
        if ($LASTEXITCODE -ne 0) { throw 'Source / independent reference checks failed.' }
    }
    & $npmCommand run build
    if ($LASTEXITCODE -ne 0) { throw 'Checked production build failed.' }
    if ($Action -eq 'Start') {
        Write-Host 'Open http://127.0.0.1:5179 on this computer. Stop with Ctrl+C.'
        Write-Host 'Loopback only. If the port is occupied, stop only a server you own; this script never kills one.'
        & $npmCommand run preview
        if ($LASTEXITCODE -ne 0) { throw 'Loopback preview stopped with an error.' }
    }
} finally {
    Pop-Location
}
