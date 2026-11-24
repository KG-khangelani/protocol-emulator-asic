# Rebuild both VM programs and the native PIO image and compare all pin traces.
[CmdletBinding()]
param([string]$PioTools, [string]$Pdk)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$outputPath = Join-Path $repoPath ('build/spi-comparison-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $outputPath
$workbench = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
$node = 'node@sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920'
$base = @('run','--rm','--mount',"type=bind,source=$repoPath,target=/workspace,readonly",
          '--mount',"type=bind,source=$outputPath,target=/workspace/build",'--tmpfs','/tmp',
          '-w','/workspace','-e','PYTHONDONTWRITEBYTECODE=1','-e','GIT_CONFIG_COUNT=1',
          '-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/workspace')
function Invoke-ReplayDocker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "SPI comparison stage failed with exit $LASTEXITCODE" }
}
if (!$PioTools) {
    Invoke-ReplayDocker ($base + @($workbench,'python3','-B',
        'evidence/E0049-review-council/panel-a/pio/fetch_pio_tools.py','build/pio-tools'))
    $PioTools = Join-Path $outputPath 'pio-tools'
}
if (!$Pdk) {
    Invoke-ReplayDocker ($base + @($workbench,'python3','-B',
        'evidence/E0049-review-council/panel-c/fetch_pdk_models.py','--out','build/pdk'))
    $Pdk = Join-Path $outputPath 'pdk'
}
$toolsPath = (Resolve-Path -LiteralPath $PioTools).Path
$pdkPath = (Resolve-Path -LiteralPath $Pdk).Path
$base += @('--network','none','--mount',"type=bind,source=$toolsPath,target=/pio-tools,readonly",
           '--mount',"type=bind,source=$pdkPath,target=/pdk,readonly")
$runner = 'experiments/spi_target/run.py'
$out = 'build/comparison'
Invoke-ReplayDocker ($base + @($workbench,'python3','-B',$runner,'prepare',$out))
Invoke-ReplayDocker ($base + @($workbench,'python3','-B',$runner,'rtl',$out))
Invoke-ReplayDocker ($base + @($workbench,'python3','-B',$runner,'gate',$out))
Invoke-ReplayDocker ($base + @($node,'node','experiments/spi_target/pio.cjs','/pio-tools',$out))
Invoke-ReplayDocker ($base + @($workbench,'python3','-B','evidence/E0055-spi-target-comparison/audit.py','--fresh',$out))
Write-Output $outputPath
