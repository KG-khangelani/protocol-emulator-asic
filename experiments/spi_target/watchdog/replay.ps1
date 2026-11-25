# Rebuild one watchdog verification suite in a fresh workbench directory.
[CmdletBinding()]
param(
    [ValidateSet('rtl','gate','verilator','controls')][string]$Backend = 'rtl',
    [ValidateSet('baseline','stress','ties')][string]$Suite = 'baseline',
    [string]$Pdk,
    [string]$Image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$outputPath = Join-Path $repoPath ('build/spi-watchdog-replay-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $outputPath
$base = @('run','--rm','--mount',"type=bind,source=$repoPath,target=/workspace,readonly",
          '--mount',"type=bind,source=$outputPath,target=/workspace/build",'--tmpfs','/tmp',
          '-w','/workspace','-e','PYTHONDONTWRITEBYTECODE=1','-e','GIT_CONFIG_COUNT=1',
          '-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/workspace')
function Invoke-Workbench([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "SPI watchdog verification exited with $LASTEXITCODE" }
}
if ($Backend -eq 'gate') {
    if (!$Pdk) {
        Invoke-Workbench ($base + @($Image,'python3','-B',
            'evidence/E0049-review-council/panel-c/fetch_pdk_models.py','--out','build/pdk'))
        $Pdk = Join-Path $outputPath 'pdk'
    }
    $pdkPath = (Resolve-Path -LiteralPath $Pdk).Path
    $base += @('--mount',"type=bind,source=$pdkPath,target=/pdk,readonly")
}
$base += @('--network','none',$Image,'python3','-B')
$folder = 'experiments/spi_target/watchdog'
if ($Backend -eq 'controls') {
    Invoke-Workbench ($base + @("$folder/controls.py",'build/run'))
} else {
    $command = @("$folder/verify.py",'build/run')
    if ($Backend -eq 'gate') { $command += @('--pdk','/pdk') }
    if ($Backend -eq 'verilator') { $command += '--verilator' }
    if ($Suite -eq 'stress') { $command += '--stress' }
    if ($Suite -eq 'ties') { $command += '--edge-ties' }
    Invoke-Workbench ($base + $command)
}
Invoke-Workbench ($base + @('evidence/E0056-spi-target-watchdog/audit.py','--compare','build/run','--suite',$Suite))
Write-Output $outputPath
