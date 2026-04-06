<#
.SYNOPSIS
    Creates a VoxChart desktop shortcut on Windows.
    Works for both:
      - Compiled EXE  (dist\VoxChart\VoxChart.exe)
      - Dev/Python    (run_app_windows.bat)

.USAGE
    Right-click PowerShell -> Run as Administrator (optional)
    .\create_desktop_shortcut.ps1

    Force dev mode even if EXE exists:
    .\create_desktop_shortcut.ps1 -DevMode
#>

param(
    [switch]$DevMode
)

$AppName     = "VoxChart"
$ShortcutName = "VoxChart.lnk"
$Desktop     = [Environment]::GetFolderPath('Desktop')
$RepoRoot    = $PSScriptRoot
$IconSearch  = @(
    (Join-Path $RepoRoot 'assets\voxchart.ico'),
    (Join-Path $RepoRoot 'assets\icon.ico'),
    (Join-Path $RepoRoot 'icon.ico')
)

# ── Locate icon ────────────────────────────────────────────────
$IconPath = $null
foreach ($p in $IconSearch) {
    if (Test-Path $p) { $IconPath = $p; break }
}

# ── Decide target: EXE or bat launcher ─────────────────────────
$ExePath  = Join-Path $RepoRoot 'dist\VoxChart\VoxChart.exe'
$BatPath  = Join-Path $RepoRoot 'run_app_windows.bat'

if (-not $DevMode -and (Test-Path $ExePath)) {
    $TargetPath      = $ExePath
    $WorkingDir      = Split-Path $ExePath
    $Arguments       = ''
    $WindowStyle     = 1   # normal
    Write-Host "[VoxChart] Using compiled EXE: $ExePath" -ForegroundColor Cyan
} elseif (Test-Path $BatPath) {
    # Launch bat via cmd so no console window flashes
    $TargetPath      = 'cmd.exe'
    $Arguments       = "/c `"$BatPath`""
    $WorkingDir      = $RepoRoot
    $WindowStyle     = 7   # minimized (hides console)
    Write-Host "[VoxChart] Using dev launcher: $BatPath" -ForegroundColor Yellow
} else {
    Write-Error "Cannot find VoxChart.exe or run_app_windows.bat in $RepoRoot"
    exit 1
}

# ── Build shortcut ──────────────────────────────────────────────
$WshShell  = New-Object -ComObject WScript.Shell
$LnkPath   = Join-Path $Desktop $ShortcutName
$Shortcut  = $WshShell.CreateShortcut($LnkPath)

$Shortcut.TargetPath       = $TargetPath
$Shortcut.Arguments        = $Arguments
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.WindowStyle      = $WindowStyle
$Shortcut.Description      = "VoxChart — Offline AI Medical Dictation"

if ($IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
    Write-Host "[VoxChart] Icon: $IconPath" -ForegroundColor Green
} elseif ($TargetPath -like '*.exe') {
    $Shortcut.IconLocation = "$TargetPath,0"
}

$Shortcut.Save()

Write-Host ""
Write-Host "✅ Desktop shortcut created!" -ForegroundColor Green
Write-Host "   Location : $LnkPath"
Write-Host "   Target   : $TargetPath $Arguments"
Write-Host ""
Write-Host "Double-click 'VoxChart' on your desktop to launch." -ForegroundColor White
