[CmdletBinding(SupportsShouldProcess)]
param([Parameter(Mandatory)][string]$SdkRoot)

$ErrorActionPreference = 'Stop'
$name = 'VisionMachine_Daily'
$image = Join-Path $SdkRoot 'system-images\android-36\default\x86_64\system.img'
if (!(Test-Path -LiteralPath $image -PathType Leaf)) {
    throw 'Install system-images;android-36;default;x86_64 in Android Studio SDK Manager, then run the launcher again.'
}
$androidUser = if ($env:ANDROID_EMULATOR_HOME) { $env:ANDROID_EMULATOR_HOME }
    elseif ($env:ANDROID_USER_HOME) { $env:ANDROID_USER_HOME }
    elseif ($env:ANDROID_SDK_HOME) { Join-Path $env:ANDROID_SDK_HOME '.android' }
    else { Join-Path $env:USERPROFILE '.android' }
$registry = if ($env:ANDROID_AVD_HOME) { $env:ANDROID_AVD_HOME } else { Join-Path $androidUser 'avd' }
$registry = [IO.Path]::GetFullPath($registry)
$data = Join-Path $registry "$name.avd"
$entry = Join-Path $registry "$name.ini"
$template = Join-Path $PSScriptRoot "$name.ini"
if (Test-Path -LiteralPath $entry) { return }
if (!$PSCmdlet.ShouldProcess($data, 'Register daily Android emulator')) { return }

$null = [IO.Directory]::CreateDirectory($registry)
$config = Join-Path $data 'config.ini'
if (!(Test-Path -LiteralPath $data)) {
    $staging = "$data.$([guid]::NewGuid().ToString('N')).tmp"
    $null = [IO.Directory]::CreateDirectory($staging)
    try {
        [IO.File]::Copy($template, (Join-Path $staging 'config.ini'), $false)
        [IO.Directory]::Move($staging, $data)
    } finally {
        if ([IO.Directory]::Exists($staging)) {
            [IO.File]::Delete((Join-Path $staging 'config.ini'))
            [IO.Directory]::Delete($staging)
        }
    }
} elseif (!(Test-Path -LiteralPath $config -PathType Leaf) -or
    (Get-FileHash -LiteralPath $config).Hash -ne (Get-FileHash -LiteralPath $template).Hash) {
    throw "The unregistered directory $data already exists. Inspect it before registering this AVD."
}
# Publish the pointer only after the complete configuration is available.
$temporary = "$entry.$([guid]::NewGuid().ToString('N')).tmp"
try {
    [IO.File]::WriteAllLines($temporary, @('avd.ini.encoding=UTF-8', "path=$data", 'target=android-36'), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temporary, $entry)
} finally {
    if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
}
