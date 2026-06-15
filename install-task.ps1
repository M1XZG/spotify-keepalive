<#
Registers the Spotify keep-alive watchdog as a Windows Scheduled Task so it
runs automatically at logon and restarts if it ever stops.

Run this ONCE from an elevated (Administrator) PowerShell:
    .\install-task.ps1

To remove it later:
    Unregister-ScheduledTask -TaskName "SpotifyKeepAlive" -Confirm:$false
#>

$ErrorActionPreference = "Stop"

$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $here ".venv\Scripts\pythonw.exe"   # windowless interpreter
$script = Join-Path $here "keepalive.py"

if (-not (Test-Path $python)) {
    # Fall back to whatever pythonw is on PATH if no local venv exists.
    $python = "pythonw.exe"
}

# Run a single check-and-fix pass each time (the script exits with --once),
# and let Task Scheduler repeat it every 2 minutes.
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`" --once" -WorkingDirectory $here

# Trigger at logon AND immediately, each repeating every 2 minutes indefinitely.
$repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 2)).Repetition

$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
$logonTrigger.Repetition = $repetition

$nowTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
$nowTrigger.Repetition = $repetition

$trigger = @($logonTrigger, $nowTrigger)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "SpotifyKeepAlive" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Keeps Spotify playing on a specific device." `
    -Force

Write-Host "Registered scheduled task 'SpotifyKeepAlive'." -ForegroundColor Green
Write-Host "Starting it now..." -ForegroundColor Green
Start-ScheduledTask -TaskName "SpotifyKeepAlive"
