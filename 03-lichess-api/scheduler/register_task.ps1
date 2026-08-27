<#
    Innovation extra: registers the weekly tournament automation script as a
    Windows Task Scheduler job, so it runs unattended every Monday at 00:05.

    Usage (run PowerShell as the user who should own the task):
        cd scheduler
        .\register_task.ps1

    Verify:
        Get-ScheduledTask -TaskName "LichessTournamentAutomation"
        Start-ScheduledTask -TaskName "LichessTournamentAutomation"   # manual trigger
    Remove:
        Unregister-ScheduledTask -TaskName "LichessTournamentAutomation" -Confirm:$false
#>

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python).Source
$Script = Join-Path $ProjectRoot "src\tournament_automation.py"

$Action = New-ScheduledTaskAction -Execute $Python -Argument "-m src.tournament_automation --execute" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 00:05
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName "LichessTournamentAutomation" `
    -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Weekly automated creation of Lichess arena tournaments (Part B)" `
    -Force

Write-Host "Task 'LichessTournamentAutomation' registered. It will run every Monday at 00:05."
