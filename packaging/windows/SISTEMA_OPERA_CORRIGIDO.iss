; Script Inno Setup para Sistema Opera - VERSÃO FINAL COM ÍCONES
#define AppName "SISTEMA OPERA"
#define AppVersion "1.0.0"
#define AppPublisher "Opera Fashion"
#define AppExeName "SistemaOpera.exe"
#define ConfiguradorName "CONFIGURAR_BANCO.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppId={{E5D81A21-CC47-4A3A-9C0F-2D7A6C1D49AA}}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\ICONE_SISTEMA.ico
Compression=lzma2/ultra
SolidCompression=yes
OutputDir=..\..\dist
OutputBaseFilename=SistemaOpera_Setup
SetupIconFile=..\..\icons\ICONE_SISTEMA.ico
WizardStyle=modern
WizardResizable=yes
PrivilegesRequired=admin

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; GroupDescription: "Ícones adicionais:"; Flags: unchecked

[Files]
; Arquivos principais
Source: "..\..\dist\SistemaOpera\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\SistemaOpera\{#ConfiguradorName}"; DestDir: "{app}"; Flags: ignoreversion

; Ícones
Source: "..\..\icons\ICONE_SISTEMA.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\icons\icon_config.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\icons\icon_config.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\icons\*"; DestDir: "{app}\icons"; Flags: recursesubdirs

; Pastas de dados
Source: "..\..\PAGINAS_DO_SISTEMA\*"; DestDir: "{app}\PAGINAS_DO_SISTEMA"; Flags: recursesubdirs
Source: "..\..\data\*"; DestDir: "{app}\data"; Flags: recursesubdirs

[Dirs]
Name: "{app}"
Name: "{userappdata}\SistemaOpera"
Name: "{userappdata}\SistemaOpera\config"

[Icons]
; Menu Iniciar
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\ICONE_SISTEMA.ico"
Name: "{group}\Configurar Banco de Dados"; Filename: "{app}\{#ConfiguradorName}"; IconFilename: "{app}\icon_config.ico"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\ICONE_SISTEMA.ico"

; Área de trabalho
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\ICONE_SISTEMA.ico"; Tasks: desktopicon
Name: "{autodesktop}\Configurar Banco"; Filename: "{app}\{#ConfiguradorName}"; IconFilename: "{app}\icon_config.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ConfiguradorName}"; Description: "Configurar banco de dados agora"; Flags: postinstall runasoriginaluser
Filename: "{app}\{#AppExeName}"; Description: "Executar {#AppName}"; Flags: postinstall nowait runasoriginaluser unchecked