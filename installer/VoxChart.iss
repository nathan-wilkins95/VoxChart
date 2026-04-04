[Setup]
AppId={{6F3A2B1C-9D4E-4F8A-B2C3-1A2B3C4D5E6F}}
AppName=VoxChart
AppVersion=1.0.0
AppPublisher=VoxChart
DefaultDirName={autopf}\VoxChart
DefaultGroupName=VoxChart
OutputDir=C:\medical_dictation_windows_final\installer\output
OutputBaseFilename=VoxChart_Setup_v1.0.0
SetupIconFile=C:\medical_dictation_windows_final\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName=VoxChart

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "C:\medical_dictation_windows_final\dist\VoxChart.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\medical_dictation_windows_final\medical_terms.db";     DestDir: "{app}"; Flags: ignoreversion
Source: "C:\medical_dictation_windows_final\assets\icon.ico";      DestDir: "{app}\assets"; Flags: ignoreversion

[Dirs]
Name: "{app}\chart_notes"

[Icons]
Name: "{group}\VoxChart";      Filename: "{app}\VoxChart.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\VoxChart"; Filename: "{app}\VoxChart.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\VoxChart.exe"; Description: "Launch VoxChart"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\chart_notes"
