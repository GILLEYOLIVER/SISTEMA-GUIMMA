; Script Inno Setup para Sistema Opera - VERSÃO FINAL
; Encoding: UTF-8 with BOM

#define AppName "SISTEMA OPERA"
#define AppVersion "1.0.0"
#define AppPublisher "Opera Fashion"
#define AppExeName "SistemaOpera.exe"
#define ConfiguradorName "CONFIGURAR_BANCO.exe"

[Setup]
; Informações básicas
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppId={{E5D81A21-CC47-4A3A-9C0F-2D7A6C1D49AA}}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\ICONE_SISTEMA.ico

; Configurações de compressão
Compression=lzma2/ultra
SolidCompression=yes

; Diretórios de saída
OutputDir=..\..\dist
OutputBaseFilename=SistemaOpera_Setup

; Ícone do instalador
SetupIconFile=..\..\icons\ICONE_SISTEMA.ico

; Estilo e permissões
WizardStyle=modern
WizardResizable=yes
PrivilegesRequired=admin

; Forçar UTF-8
[Code]
function IsUnicode: Boolean;
begin
  Result := True;
end;

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; GroupDescription: "Ícones adicionais:"; Flags: unchecked

[Files]
; Arquivo principal
Source: "..\..\dist\SistemaOpera\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; CONFIGURADOR DO BANCO - ARQUIVO MAIS IMPORTANTE
Source: "..\..\dist\SistemaOpera\{#ConfiguradorName}"; DestDir: "{app}"; Flags: ignoreversion

; Ícone
Source: "..\..\icons\ICONE_SISTEMA.ico"; DestDir: "{app}"; Flags: ignoreversion

; Pastas de dados
Source: "..\..\PAGINAS_DO_SISTEMA\*"; DestDir: "{app}\PAGINAS_DO_SISTEMA"; Flags: recursesubdirs
Source: "..\..\data\*"; DestDir: "{app}\data"; Flags: recursesubdirs

[Dirs]
Name: "{app}"
Name: "{userappdata}\SistemaOpera"
Name: "{userappdata}\SistemaOpera\config"
Name: "{userappdata}\SistemaOpera\logs"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\ICONE_SISTEMA.ico"
Name: "{group}\Configurar Banco"; Filename: "{app}\{#ConfiguradorName}"; IconFilename: "{app}\ICONE_SISTEMA.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\ICONE_SISTEMA.ico"; Tasks: desktopicon

[Run]
; EXECUTAR O CONFIGURADOR DURANTE A INSTALAÇÃO
Filename: "{app}\{#ConfiguradorName}"; Description: "Configurar banco de dados agora"; Flags: postinstall runascurrentuser checked
Filename: "{app}\{#AppExeName}"; Description: "Executar programa"; Flags: postinstall nowait runascurrentuser unchecked