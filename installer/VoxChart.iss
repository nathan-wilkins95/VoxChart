; ---------------------------------------------------------------
; VoxChart Inno Setup Script
; Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
;
; Before compiling:
;   1. pyinstaller --onefile --windowed --icon=assets\icon.ico --name="VoxChart" app.py
;   2. python build_medical_db.py   (generates medical_terms.db)
;   3. Open this .iss file in Inno Setup and click Build > Compile
; ---------------------------------------------------------------

#define MyAppName      "VoxChart"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "VoxChart"
#define MyAppExeName   "VoxChart.exe"
#define MyAppURL       "https://github.com/nathan-wilkins95/medical-dictation"

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
LicenseFile=
OutputDir=installer\output
OutputBaseFilename=VoxChart_Setup_v{#MyAppVersion}
SetupIconFile=assets\icon.ico
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
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional icons:"; Flags: checked

[Files]
; Main executable (built by PyInstaller)
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Pre-built medical terms database
Source: "medical_terms.db"; DestDir: "{app}"; Flags: ignoreversion

; App icon
Source: "assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

; Training corpus folder (if present)
Source: "training_corpus\*"; DestDir: "{app}\training_corpus"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{src}\training_corpus'))

[Dirs]
; Create chart_notes output folder on install
Name: "{app}\chart_notes"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\chart_notes"
Type: files; Name: "{app}\medical_terms.db"
