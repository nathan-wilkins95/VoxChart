<#
.SYNOPSIS
    Signs VoxChart.exe (and installer if present) using signtool.exe.
    Supports both self-signed (.pfx) and commercial CA certificates.

.DESCRIPTION
    Signing an EXE does two things:
      1. Proves the EXE came from you (integrity)
      2. Adds a trusted timestamp so the signature stays valid after cert expiry
    Windows SmartScreen and most antivirus products treat signed EXEs as
    far more trustworthy than unsigned ones.

.USAGE
    # Self-signed cert (create with create_self_signed_cert.ps1 first):
    .\sign_exe.ps1

    # Commercial cert PFX:
    .\sign_exe.ps1 -PfxPath "C:\certs\mycompany.pfx" -PfxPassword "mypassword"

    # Sign by cert thumbprint (cert already installed in store):
    .\sign_exe.ps1 -Thumbprint "ABCDEF1234..."

.PARAMETER PfxPath
    Path to .pfx certificate file. Defaults to .\signing\voxchart_cert.pfx

.PARAMETER PfxPassword
    Password for the .pfx file. Defaults to VoxChartSign2025

.PARAMETER Thumbprint
    Certificate thumbprint (alternative to PfxPath - looks up cert in store).

.PARAMETER TimestampUrl
    RFC 3161 timestamp server URL. Defaults to Sectigo's free timestamp server.

.PARAMETER ExePath
    Path to EXE to sign. Defaults to dist\VoxChart\VoxChart.exe
#>

param(
    [string]$PfxPath      = ".\signing\voxchart_cert.pfx",
    [string]$PfxPassword  = "VoxChartSign2025",
    [string]$Thumbprint   = "",
    [string]$TimestampUrl = "http://timestamp.sectigo.com",
    [string]$ExePath      = "",
    [string]$Description  = "VoxChart - Offline AI Medical Dictation"
)

$RepoRoot = $PSScriptRoot

# ── Find signtool.exe ───────────────────────────────────────────────
function Find-SignTool {
    # Try common Windows SDK locations
    $candidates = @(
        "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
        "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
        "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
        "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\signtool.exe"
    )
    # Also search recursively under Windows Kits
    $wkBase = "C:\Program Files (x86)\Windows Kits\10\bin"
    if (Test-Path $wkBase) {
        Get-ChildItem -Path $wkBase -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue `
            | Where-Object { $_.FullName -like "*x64*" } `
            | ForEach-Object { $candidates = @($_.FullName) + $candidates }
    }
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    # Try PATH
    $inPath = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }
    return $null
}

$SignTool = Find-SignTool
if (-not $SignTool) {
    Write-Error @"
signtool.exe not found.
Install the Windows SDK:
  https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
  (Only the 'Windows SDK Signing Tools for Desktop Apps' component is needed)
"@
    exit 1
}
Write-Host "[VoxChart] signtool: $SignTool" -ForegroundColor Gray

# ── Resolve EXE targets ────────────────────────────────────────────────
$targets = @()
if ($ExePath) {
    $targets += $ExePath
} else {
    # Default targets: main EXE + installer if present
    $defaultExe   = Join-Path $RepoRoot "dist\VoxChart\VoxChart.exe"
    $installerExe = Join-Path $RepoRoot "installer\VoxChart_Setup.exe"
    if (Test-Path $defaultExe)   { $targets += $defaultExe }
    if (Test-Path $installerExe) { $targets += $installerExe }
}

if ($targets.Count -eq 0) {
    Write-Error "No EXE files found to sign. Build the EXE first with build_exe_windows.bat"
    exit 1
}

# ── Build signtool arguments ───────────────────────────────────────────────
function Sign-File($filePath) {
    Write-Host ""
    Write-Host "[VoxChart] Signing: $filePath" -ForegroundColor Cyan

    if ($Thumbprint) {
        # Use cert from Windows certificate store by thumbprint
        $args = @(
            "sign",
            "/sha1", $Thumbprint,
            "/fd",   "SHA256",
            "/tr",   $TimestampUrl,
            "/td",   "SHA256",
            "/d",    $Description,
            "/v",
            $filePath
        )
    } elseif (Test-Path $PfxPath) {
        # Use PFX file
        $args = @(
            "sign",
            "/f",   $PfxPath,
            "/p",   $PfxPassword,
            "/fd",  "SHA256",
            "/tr",  $TimestampUrl,
            "/td",  "SHA256",
            "/d",   $Description,
            "/v",
            $filePath
        )
    } else {
        Write-Error "No certificate found. Provide -PfxPath or -Thumbprint, or run create_self_signed_cert.ps1 first."
        return $false
    }

    & $SignTool @args
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[VoxChart] Signed successfully: $filePath" -ForegroundColor Green
        return $true
    } else {
        Write-Error "Signing failed for: $filePath (exit code $LASTEXITCODE)"
        return $false
    }
}

# ── Sign all targets ──────────────────────────────────────────────────────────
$allOk = $true
foreach ($t in $targets) {
    $ok = Sign-File $t
    if (-not $ok) { $allOk = $false }
}

# ── Verify signatures ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[VoxChart] Verifying signatures..." -ForegroundColor Cyan
foreach ($t in $targets) {
    & $SignTool verify /pa /v $t
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $t" -ForegroundColor Green
    } else {
        Write-Host "  FAIL: $t" -ForegroundColor Red
        $allOk = $false
    }
}

Write-Host ""
if ($allOk) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " All files signed and verified!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " One or more files failed signing." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Timestamp server used: $TimestampUrl" -ForegroundColor Gray
Write-Host "The EXE is now signed. Windows SmartScreen and AV tools" -ForegroundColor Gray
Write-Host "will treat it as much more trustworthy." -ForegroundColor Gray
Write-Host ""
