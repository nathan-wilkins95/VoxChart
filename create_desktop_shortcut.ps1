$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut((Join-Path $Desktop 'Medical Dictation.lnk'))
$Target = Join-Path $PSScriptRoot 'dist\MedicalDictation\MedicalDictation.exe'
$Shortcut.TargetPath = $Target
$Shortcut.WorkingDirectory = Split-Path $Target
$Shortcut.IconLocation = $Target
$Shortcut.Save()
Write-Host "Desktop shortcut created:" (Join-Path $Desktop 'Medical Dictation.lnk')