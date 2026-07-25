; Inno Setup script para hotkeyconfig.
; Compilar:  python scripts\build.py --installer
;   (o)      & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" /DMyAppVersion=x.y.z installer\hotkeyconfig.iss
; Genera dist\hotkeyconfig-<version>-setup.exe a partir de dist\hotkeyconfig (build de PyInstaller).

#define MyAppName "hotkeyconfig"
#ifndef MyAppVersion
  #define MyAppVersion "0.2.0"
#endif
#define MyAppPublisher "Munir Torres"
#define MyAppURL "https://github.com/Mun1to/hotkeyconfig"
#define MyAppExeName "hotkeyconfig.exe"

[Setup]
; AppId identifica la app para actualizaciones y desinstalacion. No cambiar entre versiones.
AppId={{E8EED767-9F50-43A2-B631-69C88401E60C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\dist
OutputBaseFilename=hotkeyconfig-{#MyAppVersion}-setup
SetupIconFile=..\branding\favicon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Instala sin admin (en la carpeta del usuario) pero permite elegir para todos.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
; Si la app esta corriendo, Windows la cierra sola antes de instalar.
CloseApplications=yes
CloseApplicationsFilter=hotkeyconfig.exe
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Iniciar hotkeyconfig con Windows"; GroupDescription: "Opciones:"; Flags: unchecked

[Files]
Source: "..\dist\hotkeyconfig\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Instala el arranque automatico del listener si el usuario lo marco.
Filename: "{app}\{#MyAppExeName}"; Parameters: "autostart install"; Flags: runhidden waituntilterminated; Tasks: autostart
; Casilla "Ejecutar hotkeyconfig" al terminar.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Al desinstalar, quita el arranque automatico.
Filename: "{app}\{#MyAppExeName}"; Parameters: "autostart uninstall"; Flags: runhidden; RunOnceId: "RemoveAutostart"
