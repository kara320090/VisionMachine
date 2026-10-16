param(
  [string]$ExperimentId = '20261016T031000_KST_crop8_effb0_c901e829',
  [string]$RunName = '',
  [string]$Destination = 'C:\Users\LOCAL_USER\Desktop\ComputerVision-ai'
)
$ErrorActionPreference = 'Stop'
if ($ExperimentId -notmatch '^[A-Za-z0-9_-]+$' -or ($RunName -and $RunName -notmatch '^[ABC]_seed(17|42|2026)$')) { throw 'Invalid experiment/run identifier' }
$sshConfig = 'C:/Users/LOCAL_USER/Documents/Codex/2026-10-15/new-chat/work/ssh/config'
$remoteRoot = '/home/user/ComputerVision-ai/experiments/' + $ExperimentId
$remoteCommand = $remoteRoot + '/.venv/bin/python -B ' + $remoteRoot + '/code/transfer_bundle.py --root ' + $remoteRoot
if ($RunName) { $remoteCommand += ' --run ' + $RunName }
$output = & 'C:\WINDOWS\System32\OpenSSH\ssh.exe' -T -F $sshConfig -o BatchMode=yes school-gpu $remoteCommand
if ($LASTEXITCODE -ne 0) { throw 'Remote bundle creation failed' }
$bundle = ($output | Select-Object -Last 1) | ConvertFrom-Json
$experimentRoot = Join-Path $Destination $ExperimentId
$snapshotId = (Get-Date -Format 'yyyyMMddTHHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0,8)
$receiveRoot = Join-Path $experimentRoot ('snapshots\' + $snapshotId)
New-Item -ItemType Directory -Path $receiveRoot -ErrorAction Stop | Out-Null
$archive = Join-Path $receiveRoot 'bundle.tar'
& 'C:\WINDOWS\System32\OpenSSH\scp.exe' -F $sshConfig -o BatchMode=yes ('school-gpu:' + $bundle.bundle) $archive
if ($LASTEXITCODE -ne 0) { throw 'Transfer failed; incomplete snapshot retained' }
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $bundle.bundle_sha256) { throw 'Bundle hash mismatch' }
$members = & tar.exe -tf $archive
if ($LASTEXITCODE -ne 0) { throw 'Invalid tar archive' }
foreach ($member in $members) {
  if ($member -match '(^[/\\])|(^[A-Za-z]:)|(^|[/\\])\.\.([/\\]|$)') { throw 'Unsafe archive entry' }
}
& tar.exe -xf $archive -C $receiveRoot
if ($LASTEXITCODE -ne 0) { throw 'Extraction failed' }
$inventoryName = [IO.Path]::GetFileName($bundle.inventory)
$inventory = Get-Content -LiteralPath (Join-Path $receiveRoot ('transfer\' + $inventoryName)) -Raw | ConvertFrom-Json
$checked = 0
foreach ($entry in $inventory.files) {
  $file = Join-Path $receiveRoot $entry.path
  $resolved = [IO.Path]::GetFullPath($file)
  if (-not $resolved.StartsWith([IO.Path]::GetFullPath($receiveRoot) + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Inventory path escaped snapshot' }
  if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw ('Missing file: ' + $entry.path) }
  if ((Get-Item -LiteralPath $file).Length -ne $entry.bytes) { throw ('Size mismatch: ' + $entry.path) }
  if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw ('Hash mismatch: ' + $entry.path) }
  $checked++
}
$receipt = @{ status='verified'; time=(Get-Date).ToString('o'); files=$checked; bundle_sha256=$bundle.bundle_sha256; remote_preserved=$true; snapshot=$receiveRoot; run=$RunName }
$receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $receiveRoot 'transfer_verified.json') -Encoding utf8
Write-Output ($receipt | ConvertTo-Json -Compress)
