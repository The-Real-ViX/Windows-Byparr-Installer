#define AppName "Byparr Manager"
#ifndef AppVersion
  #define AppVersion "0.4.0"
#endif
#ifndef BuildNumber
  #define BuildNumber "DEV"
#endif
#define AppPublisher "The-Real-ViX"
#define AppExeName "ByparrManager.exe"
#define BuildDir "..\manager\dist\ByparrManager"
#define IconFile "..\manager\assets\byparr-manager.ico"

[Setup]
AppId={{F2C31A1C-7D3A-4D13-9E25-6C3A9E71B84A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Byparr Manager
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
OutputDir=..\manager\installer-output
OutputBaseFilename=ByparrManager-Setup-v{#AppVersion}-build-{#BuildNumber}-x64
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
Uninstallable=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: files; Name: "{autodesktop}\{#AppName}.lnk"
