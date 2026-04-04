; ---------------------------------------------------------------
; VoxChart Inno Setup Script
; Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
;
; Before compiling:
;   1. pyinstaller --onefile --windowed --icon=assets\icon.ico --name="VoxChart" app.py
;   2. python build_medical_db.py
;   3. Run: ISCC.exe installer\VoxChart.iss
; ---------------------------------------------------------------

#define MyAppName      "VoxChart"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "VoxChart"
#define MyAppExeName   "VoxChart.exe"
#define MyAppURL       "https://github.com/nathan-wilkins95/medical-dictation"
#define SourceDir      "C:\medical_dictation_windows_final"

[Setup]
AppId={{6F3A2B1C-9D4E-4F8A-B2C3-1A2B3C4D5E6F}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir={#SourceDir}\installer\output
OutputBaseFilename=VoxChart_Setup_v{#MyAppVersion}
SetupIconFile={#SourceDir}\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checked

[Files]
Source: "{#SourceDir}\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\medical_terms.db";     DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\assets\icon.ico";      DestDir: "{app}\assets"; Flags: ignoreversion

[Dirs]
Name: "{app}\chart_notes"

[Icons]
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\chart_notes"
Type: files;          Name: "{app}\medical_terms.db"
