; Inno Setup script: wraps dist\Lipi into a per-user installer (no admin rights needed).
#define AppVersion GetEnv("LIPI_VERSION")
#if AppVersion == ""
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6F4A2C1E-3B7D-4E58-9A21-5C0D8E7F4B13}
AppName=Lipi
AppVersion={#AppVersion}
AppPublisher=Lipi
DefaultDirName={localappdata}\Programs\Lipi
DefaultGroupName=Lipi
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Lipi-Setup
SetupIconFile=lipi.ico
UninstallDisplayIcon={app}\Lipi.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\Lipi\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Lipi"; Filename: "{app}\Lipi.exe"
Name: "{userdesktop}\Lipi"; Filename: "{app}\Lipi.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce

[Run]
Filename: "{app}\Lipi.exe"; Description: "Start Lipi now"; Flags: nowait postinstall skipifsilent
