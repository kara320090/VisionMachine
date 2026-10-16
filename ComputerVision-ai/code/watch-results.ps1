param([string]$ExperimentId='20261016T031000_KST_crop8_effb0_c901e829')
$ErrorActionPreference='Stop'
if ($ExperimentId -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid experiment id' }
$config='C:/Users/LOCAL_USER/Documents/Codex/2026-10-15/new-chat/work/ssh/config'
$remote='/home/user/ComputerVision-ai/experiments/'+$ExperimentId
$local=Join-Path 'C:\Users\LOCAL_USER\Desktop\ComputerVision-ai' $ExperimentId
$ledger=Join-Path $local 'transfer-receipts'
New-Item -ItemType Directory -Path $ledger -Force | Out-Null
$expected=@('A_seed17','B_seed17','C_seed17','A_seed42','B_seed42','C_seed42','A_seed2026','B_seed2026','C_seed2026')
while ($true) {
  # Only fixed, validated identifiers are interpolated into this SSH command.
  $command="find $remote/runs -mindepth 2 -maxdepth 2 -name completed.json -type f"
  $completed=& 'C:\WINDOWS\System32\OpenSSH\ssh.exe' -T -F $config -o BatchMode=yes -o ConnectTimeout=15 school-gpu $command
  if ($LASTEXITCODE -eq 0) {
    foreach ($item in $completed) {
      $run=($item -split '/')[-2]
      if (($expected -contains $run) -and -not (Test-Path -LiteralPath (Join-Path $ledger ($run+'.json')))) {
        $receipt=& (Join-Path $PSScriptRoot 'sync-results.ps1') -ExperimentId $ExperimentId -RunName $run
        $receipt | Set-Content -LiteralPath (Join-Path $ledger ($run+'.json')) -Encoding utf8
      }
    }
    $allDone=($expected | Where-Object { -not (Test-Path -LiteralPath (Join-Path $ledger ($_+'.json'))) }).Count -eq 0
    if ($allDone) {
      & 'C:\WINDOWS\System32\OpenSSH\ssh.exe' -T -F $config -o BatchMode=yes school-gpu "test -f $remote/runs/suite_completed.json"
      if ($LASTEXITCODE -eq 0) {
        & (Join-Path $PSScriptRoot 'sync-results.ps1') -ExperimentId $ExperimentId
        break
      }
    }
  }
  Start-Sleep -Seconds 30
}
