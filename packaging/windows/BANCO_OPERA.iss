; Instalador dedicado de Banco de Dados (Servidor)
#define AppName "OPERA - BANCO DE DADOS"
#define AppVersion "1.0.0"
#define AppPublisher "Opera Fashion"
#define DbConfigExe "CONFIGURAR_BANCO.exe"
#define AutoSetupExe "AUTO_SERVER_SETUP.exe"

#if FileExists("..\..\dist\SistemaOpera\CONFIGURAR_BANCO.exe")
  #define DbConfigSource "..\..\dist\SistemaOpera\CONFIGURAR_BANCO.exe"
#else
  #define DbConfigSource "..\..\dist\windows\CONFIGURAR_BANCO.exe"
#endif

#if FileExists("..\..\dist\SistemaOpera\AUTO_SERVER_SETUP.exe")
  #define AutoServerSetupSource "..\..\dist\SistemaOpera\AUTO_SERVER_SETUP.exe"
#else
  #define AutoServerSetupSource "..\..\dist\windows\AUTO_SERVER_SETUP.exe"
#endif

#if FileExists("..\..\icons\icon_config.ico")
  #define SetupIcon "..\..\icons\icon_config.ico"
#else
  #define SetupIcon "..\..\icons\ICONE_SISTEMA.ico"
#endif

[Setup]
AppName={#AppName}
AppVerName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppId={{D0F35556-2519-43DA-A2E6-9DBAB46FF1CB}}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
Compression=lzma2/ultra
SolidCompression=yes
OutputDir=..\..\dist
OutputBaseFilename=BancoDadosOpera_Setup
SetupIconFile={#SetupIcon}
WizardStyle=modern
WizardResizable=yes
PrivilegesRequired=admin

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar icone na area de trabalho"; GroupDescription: "Icones adicionais:"; Flags: unchecked

[Files]
Source: "{#DbConfigSource}"; DestDir: "{app}"; DestName: "{#DbConfigExe}"; Flags: ignoreversion
Source: "{#AutoServerSetupSource}"; DestDir: "{app}"; DestName: "{#AutoSetupExe}"; Flags: ignoreversion
Source: "..\..\auto_server_setup.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\opera_server_config.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\installer_scripts\windows\server_quick_setup.ps1"; DestDir: "{app}"; Flags: ignoreversion

; Instalador PostgreSQL opcional na raiz do projeto
Source: "..\..\postgresql-18*-windows-*.exe"; DestDir: "{app}\postgresql"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\postgresql*-windows-*.exe"; DestDir: "{app}\postgresql"; Flags: ignoreversion skipifsourcedoesntexist

Source: "..\..\icons\ICONE_SISTEMA.ico"; DestDir: "{app}"; Flags: ignoreversion
#if FileExists("..\..\icons\icon_config.ico")
Source: "..\..\icons\icon_config.ico"; DestDir: "{app}"; Flags: ignoreversion
#endif

[Icons]
Name: "{group}\Setup rapido servidor"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\server_quick_setup.ps1"""; IconFilename: "{app}\ICONE_SISTEMA.ico"
Name: "{group}\Configurar Banco Manual"; Filename: "{app}\{#DbConfigExe}"; IconFilename: "{app}\ICONE_SISTEMA.ico"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\ICONE_SISTEMA.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\server_quick_setup.ps1"""; Tasks: desktopicon; IconFilename: "{app}\ICONE_SISTEMA.ico"

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\server_quick_setup.ps1"""; Description: "Executar setup automático do servidor (PostgreSQL + banco + server_info)"; Flags: postinstall waituntilterminated
Filename: "{app}\{#DbConfigExe}"; Description: "Abrir configurador manual do banco"; Flags: postinstall runasoriginaluser unchecked
