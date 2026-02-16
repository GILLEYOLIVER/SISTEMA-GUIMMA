; Script Inno Setup para Sistema Opera - VERSAO FINAL (SEM VERSAO NA LISTA)
#define AppName "SISTEMA OPERA FASHION"
#define AppVersion "1.0.0"
#define AppPublisher "Opera Fashion"
#define AppExeName "SistemaOpera.exe"
#define ConfiguradorName "CONFIGURAR_BANCO.exe"

; === Seleciona fontes automaticamente (dist/windows ou dist/SistemaOpera) ===
#if FileExists("..\..\dist\windows\SistemaOpera.exe")
  #define MainExeSource "..\..\dist\windows\SistemaOpera.exe"
#else
  #define MainExeSource "..\..\dist\SistemaOpera\SistemaOpera.exe"
#endif

#if FileExists("..\..\dist\SistemaOpera\CONFIGURAR_BANCO.exe")
  #define DbConfigSource "..\..\dist\SistemaOpera\CONFIGURAR_BANCO.exe"
#else
  #define DbConfigSource "..\..\dist\windows\CONFIGURAR_BANCO.exe"
#endif

; Icone do configurador: prioriza icon_config.ico, senao usa configurador.ico gerado no build
#if FileExists("..\..\icons\icon_config.ico")
  #define IconConfigSource "..\..\icons\icon_config.ico"
#elif FileExists("..\..\dist\SistemaOpera\configurador.ico")
  #define IconConfigSource "..\..\dist\SistemaOpera\configurador.ico"
#elif FileExists("..\..\build\configurador.ico")
  #define IconConfigSource "..\..\build\configurador.ico"
#else
  ; fallback: usa o icone principal
  #define IconConfigSource "..\..\icons\ICONE_SISTEMA.ico"
#endif

[Setup]
AppName={#AppName}
; IMPORTANTE: nao concatenar nome + versao no nome exibido
AppVerName={#AppName}
; Mantemos AppVersion internamente, mas vamos zerar DisplayVersion no registro
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppId={{E5D81A21-CC47-4A3A-9C0F-2D7A6C1D49AA}}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\ICONE_SISTEMA.ico
Compression=lzma2/ultra
SolidCompression=yes
OutputDir=..\..\dist
OutputBaseFilename=SistemaOpera_Setup
SetupIconFile=..\..\icons\ICONE_SISTEMA.ico
WizardStyle=modern
WizardResizable=yes
PrivilegesRequired=admin

[Registry]
; Nao gravar versao na lista de programas (zera DisplayVersion)
; Instalacao como Admin (HKLM)
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting('AppId')}_is1"; ValueType: string; ValueName: "DisplayVersion"; ValueData: ""; Check: IsAdminInstallMode; Flags: uninsdeletevalue
; Instalacao por usuario (HKCU) â€“ se algum dia mudar PrivilegesRequired
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting('AppId')}_is1"; ValueType: string; ValueName: "DisplayVersion"; ValueData: ""; Check: not IsAdminInstallMode; Flags: uninsdeletevalue

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar icone na area de trabalho"; GroupDescription: "Icones adicionais:"; Flags: unchecked

[Files]
; Arquivos principais
Source: "{#MainExeSource}"; DestDir: "{app}"; DestName: "{#AppExeName}"; Flags: ignoreversion
Source: "{#DbConfigSource}"; DestDir: "{app}"; DestName: "{#ConfiguradorName}"; Flags: ignoreversion

; Icones (copiados direto para {app} para usar no Menu/Atalhos)
Source: "..\..\icons\ICONE_SISTEMA.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#IconConfigSource}"; DestDir: "{app}"; DestName: "icon_config.ico"; Flags: ignoreversion

#if FileExists("..\..\icons\icon_config.png")
Source: "..\..\icons\icon_config.png"; DestDir: "{app}"; DestName: "icon_config.png"; Flags: ignoreversion
#endif

; Copia a pasta icons inteira (se existir) para {app}\icons
#if DirExists("..\..\icons")
Source: "..\..\icons\*"; DestDir: "{app}\icons"; Flags: recursesubdirs createallsubdirs
#endif

; Pastas de dados
Source: "..\..\PAGINAS_DO_SISTEMA\*"; DestDir: "{app}\PAGINAS_DO_SISTEMA"; Flags: recursesubdirs createallsubdirs
Source: "..\..\data\*"; DestDir: "{app}\data"; Flags: recursesubdirs createallsubdirs

[Dirs]
Name: "{app}"
Name: "{userappdata}\SistemaOpera"
Name: "{userappdata}\SistemaOpera\config"

[Icons]
; Menu Iniciar
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\ICONE_SISTEMA.ico"
Name: "{group}\Configurar Banco de Dados"; Filename: "{app}\{#ConfiguradorName}"; IconFilename: "{app}\icon_config.ico"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\ICONE_SISTEMA.ico"

; Area de trabalho
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\ICONE_SISTEMA.ico"; Tasks: desktopicon
Name: "{autodesktop}\Configurar Banco"; Filename: "{app}\{#ConfiguradorName}"; IconFilename: "{app}\icon_config.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ConfiguradorName}"; Description: "Configurar banco de dados agora"; Flags: postinstall runasoriginaluser
Filename: "{app}\{#AppExeName}"; Description: "Executar {#AppName}"; Flags: postinstall nowait runasoriginaluser unchecked
