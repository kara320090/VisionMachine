# Windows PC USB diagnostic. Emits actual JSONL; does not write records to Git.
param(
 [Parameter(Mandatory=$true)][string]$Port,
 [ValidateSet('basic','extended')][string]$Profile='extended',
 [ValidateRange(1,100)][int]$Count=1
)
$ErrorActionPreference='Stop'
$serial=[IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.NewLine="`n"
$serial.ReadTimeout=12000
$serial.WriteTimeout=3000
$serial.DtrEnable=$true
$serial.RtsEnable=$false
try {
 $serial.Open()
 Start-Sleep -Milliseconds 1500
 $serial.DiscardInBuffer()
 for($sample=0;$sample -lt $Count;$sample++) {
  $requestId=[Guid]::NewGuid().ToString()
  $request=[ordered]@{schema_version='0.1.0';message_type='measure';request_id=$requestId;sensor_profile=$Profile}
  $serial.WriteLine(($request | ConvertTo-Json -Compress))
  $line=$serial.ReadLine().Trim()
  $packet=$line | ConvertFrom-Json
  if($packet.request_id -cne $requestId -or $packet.message_type -ne 'measurement' -or
     $packet.schema_version -ne '0.1.0' -or $packet.mode -ne 'real') {
   throw 'Unexpected USB packet or stale request ID. Do not use this reading.'
  }
  if($Profile -eq 'extended' -and $null -eq $packet.extensions) {
   throw 'Extended response absent. Upload firmware v0.2.0 or later.'
  }
  Write-Output $line
 }
} finally {
 if($serial.IsOpen){$serial.Close()}
 $serial.Dispose()
}
