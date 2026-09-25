Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\data analyst\ai-data-analyst-os\scripts\start_app_on_boot.ps1""", 0, False
Set WshShell = Nothing
