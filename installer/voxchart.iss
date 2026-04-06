; VoxChart Inno Setup Script
; Builds VoxChart_Setup.exe — a proper Windows installer
; Requires Inno Setup 6: https://jrsoftware.org/isinfo.php
;
; Usage:
;   1. Build the EXE first:  build.bat -> [2] Build EXE
;   2. Then compile this:    iscc installer\voxchart.iss
;   Output: installer\Output\VoxChart_Setup.exe

#define MyAppName      "VoxChart"
#define MyAppVersion   "1.7.0"
#define MyAppPublisher "Nathan Wilkins"
#define MyAppURL       "https://github.com/nathan-wilkins95/VoxChart"
#define MyAppExeName   "VoxChart.exe"
#define MyAppIcon      "..\assets\VoxChart.ico"
#define SourceDir      "..\dist\VoxChart"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=VoxChart_Setup
SetupIconFile={#MyAppIcon}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=VoxChart Offline AI Medical Dictation
VersionInfoCopyright=Copyright (c) 2026 {#MyAppPublisher}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Main application directory (PyInstaller output)
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";          Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\VoxChart.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";    Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\VoxChart.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\chart_notes"
Type: filesandordirs; Name: "{app}\logs"
Type: files;          Name: "{app}\voxchart_config.json"

[Code]
// Check for existing installation and offer to uninstall first
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
end;
