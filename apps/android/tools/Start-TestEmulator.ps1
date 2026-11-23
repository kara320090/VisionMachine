[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidatePattern('^[\w][\w.-]*$')][string]$AvdName = 'VisionMachine_Release_UI_Test',
    [string]$DataDirectory,
    [switch]$ReadOnly,
    [switch]$ShowWindow,
    [ValidateRange(5554,5682)][int]$Port = 5576,
    [ValidateRange(5,600)][int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
if ($Port % 2) { throw 'The emulator console port must be even.' }
$explicitPort = $PSBoundParameters.ContainsKey('Port')
$sdk = @($env:ANDROID_HOME, $env:ANDROID_SDK_ROOT, (Join-Path $env:LOCALAPPDATA 'Android\Sdk')) |
    Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $_ 'emulator\emulator.exe')) -and
        (Test-Path -LiteralPath (Join-Path $_ 'platform-tools\adb.exe')) } | Select-Object -First 1
if (!$sdk) { throw 'Android SDK emulator and platform-tools are required.' }
$adb = Join-Path $sdk 'platform-tools\adb.exe'
$emulator = Join-Path $sdk 'emulator\emulator.exe'
$directory = if ($DataDirectory) {
    $entry = Get-Item -LiteralPath $DataDirectory
    if (!$entry.PSIsContainer) { throw 'DataDirectory must be an existing directory.' }
    $entry.FullName.TrimEnd('\')
}

function Get-ArgumentValue([string]$commandLine, [string]$key) {
    if ($commandLine -match "(?:^|\s)-$key\s+(?:\x22([^\x22]+)\x22|([^\s\x22]+))") {
        return ($Matches[1] + $Matches[2])
    }
}

# adb can wait indefinitely if an emulator disappears between listing and querying it.
function Read-Adb([string]$arguments) {
    $query = [Diagnostics.Process]::new()
    try {
        $query.StartInfo.FileName = $adb
        $query.StartInfo.Arguments = $arguments
        $query.StartInfo.UseShellExecute = $false
        $query.StartInfo.CreateNoWindow = $true
        $query.StartInfo.RedirectStandardOutput = $true
        $query.StartInfo.RedirectStandardError = $true
        $null = $query.Start()
        $output = $query.StandardOutput.ReadToEndAsync()
        $null = $query.StandardError.ReadToEndAsync()
        if (!$query.WaitForExit(5000)) { $query.Kill(); return }
        if ($query.ExitCode -eq 0 -and $output.Wait(1000)) {
            $output.Result.Trim() -split '\r*\n'
        }
    } finally { $query.Dispose() }
}

$timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
$watch = [Diagnostics.Stopwatch]::StartNew()
$mutex = [Threading.Mutex]::new($false, ("Local\VisionMachine.Emulator." + $AvdName.ToLowerInvariant()))
$locked = $false
$launcher = $null
try {
    try { $locked = $mutex.WaitOne($timeout) }
    catch [Threading.AbandonedMutexException] { $locked = $true }
    if (!$locked) { throw "Timed out waiting for another $AvdName startup." }

    while ($watch.Elapsed -lt $timeout) {
        $processes = @(Get-CimInstance Win32_Process -Filter "Name='emulator.exe' OR Name LIKE 'qemu-system-%'" |
            Where-Object { (Get-ArgumentValue $_.CommandLine 'avd') -eq $AvdName -or
                $_.CommandLine -match ('(?:^|\s)@' + [regex]::Escape($AvdName) + '(?:\s|$)') })
        $vms = @($processes | Where-Object Name -like 'qemu-system-*')
        $devices = @(Read-Adb 'devices -l')
        if (!($devices -match '^List of devices attached')) { throw 'adb devices failed or timed out.' }
        $online = @($devices | Where-Object { $_ -match '^emulator-\d+\s+device\s' })

        $compatible = $false
        $headlessMatch = $false
        foreach ($vm in $vms) {
            $argsLine = $vm.CommandLine
            $actualDir = Get-ArgumentValue $argsLine 'datadir'
            if ($actualDir) {
                if (![IO.Path]::IsPathRooted($actualDir)) { continue }
                $actualDir = [IO.Path]::GetFullPath($actualDir).TrimEnd('\')
            }
            if ([string]$actualDir -ne [string]$directory -or
                [bool]$ReadOnly -ne ($argsLine -match '(?:^|\s)-read-only(?:\s|$)')) { continue }
            $vmPort = Get-ArgumentValue $argsLine 'port'
            if (($explicitPort -or $launcher) -and $vmPort -and [int]$vmPort -ne $Port) { continue }
            if ($ShowWindow -and $argsLine -match '(?:^|\s)-no-window(?:\s|$)') {
                $headlessMatch = $true
                continue
            }
            $compatible = $true
            foreach ($row in $online) {
                if ($row -notmatch '^(emulator-(\d+))\s+.*transport_id:(\d+)') { continue }
                $serial = $Matches[1]; $consolePort = [int]$Matches[2]; $transport = $Matches[3]
                if ((($explicitPort -or $launcher) -and $consolePort -ne $Port) -or ($vmPort -and [int]$vmPort -ne $consolePort)) { continue }
                if (!$vmPort -and !(Get-NetTCPConnection -LocalPort $consolePort -State Listen -OwningProcess $vm.ProcessId -ErrorAction SilentlyContinue)) { continue }
                $names = @(Read-Adb "-s $serial emu avd name")
                if ($names -notcontains $AvdName) { continue }
                $booted = Read-Adb "-t $transport shell getprop sys.boot_completed"
                if ($booted -ne '1') { continue }
                $gles = Read-Adb "-t $transport shell dumpsys SurfaceFlinger | grep -m 1 GLES:"
                if ("$gles" -notmatch 'GLES:') { continue }
                if ("$gles" -match 'SwiftShader|llvmpipe|lavapipe|software rasterizer') {
                    throw "$serial is using software graphics. Its session was left running."
                }
                return $serial
            }
        }
        if ($headlessMatch -and !$compatible) { throw "$AvdName is already running without a window. Finish the current session before starting an interactive one." }
        if ($vms.Count -and !$compatible) { throw "$AvdName is already running with a different port, data directory or access mode." }
        if ($launcher -and $launcher.HasExited -and !$processes.Count) { throw "Emulator exited with status $($launcher.ExitCode)." }
        if (!$launcher -and !$processes.Count) {
            foreach ($row in $online) {
                $serial = ($row -split '\s+')[0]
                $names = @(Read-Adb "-s $serial emu avd name")
                if ($names -contains $AvdName) { throw "Found $serial but could not verify its local launch arguments." }
            }
            $inUse = [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners().Port
            if ($Port -in $inUse -or ($Port + 1) -in $inUse) { throw "Emulator ports $Port/$($Port + 1) are busy." }
            $available = @(& $emulator -list-avds)
            if ($LASTEXITCODE -ne 0 -or $available -notcontains $AvdName) { throw "AVD '$AvdName' was not found in the local SDK." }
            $arguments = @('-avd', $AvdName, '-port', $Port, '-gpu', 'host', '-no-audio')
            if (!$ShowWindow) { $arguments += '-no-window' }
            if ($directory) { $arguments += @('-datadir', ('"{0}\."' -f $directory)) }
            if ($ReadOnly) { $arguments += @('-read-only', '-no-snapshot') }
            if (!$PSCmdlet.ShouldProcess("$AvdName on port $Port", ("Start emulator " + ($arguments -join ' ')))) { return }
            $launcher = Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Hidden -PassThru
        }
        Start-Sleep -Seconds 2
    }
    throw "Timed out waiting for $AvdName to finish booting with matching settings. Inspect adb devices -l."
} catch {
    # Only close a console whose listening process is a child of our still-live launcher.
    if ($launcher -and !$launcher.HasExited) {
        $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($launcher.Id) AND Name LIKE 'qemu-system-%'" -ErrorAction SilentlyContinue)
        $owners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
        if ($owners | Where-Object { $_.OwningProcess -in $children.ProcessId }) {
            $null = Read-Adb "-s emulator-$Port emu kill"
            $null = $launcher.WaitForExit(3000)
        }
        if (!$launcher.HasExited -and $ReadOnly) {
            $owned = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($launcher.Id) AND Name LIKE 'qemu-system-%'" -ErrorAction SilentlyContinue)
            foreach ($child in $owned) {
                if ((Get-ArgumentValue $child.CommandLine 'port') -eq "$Port") {
                    Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
                }
            }
            if (!$launcher.HasExited) { $launcher.Kill() }
        } elseif (!$launcher.HasExited) {
            Write-Warning "Writable emulator launcher PID $($launcher.Id) is still running. Inspect it before stopping it."
        }
    }
    throw
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
