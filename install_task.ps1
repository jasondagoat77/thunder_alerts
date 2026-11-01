# Registers a Windows scheduled task that runs thunder_alerts.py every 5 minutes (hidden, no console window).
# Run once:  powershell -ExecutionPolicy Bypass -File C:\Users\bexst\thunder-alerts\install_task.ps1
# To remove: Unregister-ScheduledTask -TaskName "Thunder Game Alerts" -Confirm:$false

$dir = "C:\Users\bexst\thunder-alerts"
$action = New-ScheduledTaskAction -Execute "C:\Users\bexst\AppData\Local\Microsoft\WindowsApps\pythonw.exe" `
    -Argument "`"$dir\thunder_alerts.py`"" -WorkingDirectory $dir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Register-ScheduledTask -TaskName "Thunder Game Alerts" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Pings phone via ntfy when OKC Thunder games start/end" -Force | Select-Object TaskName, State
