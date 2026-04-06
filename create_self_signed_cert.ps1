<#
.SYNOPSIS
    Creates a self-signed code signing certificate for VoxChart.
    Good for internal use, dev machines, and testing.
    For public distribution, use a real CA certificate (Sectigo, DigiCert, etc.)

.DESCRIPTION
    This script:
      1. Creates a self-signed cert in the current user's certificate store
      2. Exports it as a .pfx file so sign_exe.ps1 can use it
      3. Optionally installs it into Trusted Root so Windows stops flagging it

.USAGE
    Run once as Administrator:
    .\create_self_signed_cert.ps1

.NOTES
    Self-signed certs WILL still show a SmartScreen warning on first run
    on other machines unless those machines import the cert.
    For no warnings on all machines -> buy a certificate from:
      - Sectigo (cheapest, ~$80/yr)  https://sectigo.com
      - DigiCert                     https://digicert.com
      - Certum Open Source (free for open source projects)
#>

param(
    [string]$CertName    = "VoxChart",
    [string]$Publisher   = "VoxChart Medical Dictation",
    [string]$PfxPassword = "VoxChartSign2025",
    [string]$PfxOutput   = ".\signing\voxchart_cert.pfx",
    [switch]$TrustLocally
)

# Ensure signing directory exists
$SignDir = Split-Path $PfxOutput -Parent
New-Item -ItemType Directory -Force -Path $SignDir | Out-Null

Write-Host ""
Write-Host "[VoxChart] Creating self-signed code signing certificate..." -ForegroundColor Cyan
Write-Host "  Subject : CN=$Publisher"
Write-Host "  Expires : $(([datetime]::Today).AddYears(3).ToShortDateString())"
Write-Host ""

# Create cert in CurrentUser\My store
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=$Publisher" `
    -FriendlyName $CertName `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter ([datetime]::Today.AddYears(3)) `
    -KeyUsage DigitalSignature `
    -KeyAlgorithm RSA `
    -KeyLength 4096

if (-not $cert) {
    Write-Error "Certificate creation failed."
    exit 1
}

Write-Host "[VoxChart] Certificate created: $($cert.Thumbprint)" -ForegroundColor Green

# Export to PFX
$securePass = ConvertTo-SecureString -String $PfxPassword -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $PfxOutput -Password $securePass | Out-Null

Write-Host "[VoxChart] Exported to: $PfxOutput" -ForegroundColor Green

# Optionally trust locally (removes SmartScreen on this machine only)
if ($TrustLocally) {
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store(
        [System.Security.Cryptography.X509Certificates.StoreName]::Root,
        [System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine
    )
    $rootStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $rootStore.Add($cert)
    $rootStore.Close()
    Write-Host "[VoxChart] Certificate trusted locally (LocalMachine\Root)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " DONE. Next step:" -ForegroundColor Cyan
Write-Host "   Run: .\sign_exe.ps1" -ForegroundColor White
Write-Host "" 
Write-Host " PFX file  : $PfxOutput"
Write-Host " Password  : $PfxPassword"
Write-Host " Thumbprint: $($cert.Thumbprint)"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NOTE: Self-signed certs will still trigger SmartScreen on OTHER machines." -ForegroundColor Yellow
Write-Host "For public distribution, get a commercial cert (Sectigo ~$80/yr)." -ForegroundColor Yellow
Write-Host ""
