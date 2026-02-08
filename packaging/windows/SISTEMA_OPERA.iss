#define AppName "SISTEMA OPERA"
#define AppVersion "1.0.0"
#define AppPublisher "Opera Fashion"
#define AppExeName "SistemaOpera.exe"

[Setup]
AppId={{E5D81A21-CC47-4A3A-9C0F-2D7A6C1D49AA}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=Instalador_{#AppName}
OutputDir=..\..
Compression=lzma
SolidCompression=yes
DisableDirPage=no
WizardStyle=modern

; Opcional: se tiver um .ico, ajuste aqui.
SetupIconFile=..\..\PAGINAS_DO_SISTEMA\ICONE_SISTEMA.ico

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\..\dist\SistemaOpera\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\SistemaOpera\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
