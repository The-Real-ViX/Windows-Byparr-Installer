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

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    if MsgBox(
      'Would you also like to remove your saved Byparr Manager settings, browser cache, and Prowlarr/Jackett API keys from this computer?' + #13#10 + #13#10 +
      'Choose No to keep this personal data for a future reinstall. This full cleanup cannot be undone.',
      mbConfirmation, MB_YESNO
    ) = IDYES then
    begin
      if FileExists(ExpandConstant('{app}\\ByparrManager.exe')) then
      begin
        if (not Exec(
          ExpandConstant('{app}\\ByparrManager.exe'),
          '--full-uninstall-cleanup',
          ExpandConstant('{app}'),
          SW_HIDE,
          ewWaitUntilTerminated,
          ResultCode
        )) or (ResultCode <> 0) then
        begin
          MsgBox(
            'The full cleanup could not be completed. The application will still be uninstalled, but some settings, cache, or saved credentials may remain.',
            mbError, MB_OK
          );
        end;
      end
      else
      begin
        MsgBox(
          'The cleanup helper was not found. The application will still be uninstalled, but personal settings, cache, or saved credentials may remain.',
          mbError, MB_OK
        );
      end;
    end;
  end;
end;
