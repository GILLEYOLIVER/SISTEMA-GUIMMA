; Script Inno Setup para Sistema Guimma - SEM VERSAO NA LISTA
#define AppName "SISTEMA GUIMMA"
#define AppVersion "1.0.0"
#define AppPublisher "Sistema Guimma"
#define AppExeName "SistemaGuimma.exe"
#define ConfiguradorName "CONFIGURAR_BANCO.exe"
#define LicencaName "SistemaGuimmaLicenca.exe"

#ifndef ARCH
  #define ARCH "x64"
#endif

; ============================================================
;  Detecta automaticamente se o build do app principal Ã©:
;   - onedir (pasta com _internal)  -> copia a pasta inteira
;   - onefile (exe Ãºnico)           -> copia sÃ³ o exe
;  Prioridade: dist\SistemaGuimma -> dist\windows\SistemaGuimma -> exe solto
; ============================================================

#if DirExists("..\\..\\dist\\SistemaGuimma\\_internal")
  #define MainIsOneDir 1
  #define MainDirSource "..\\..\\dist\\SistemaGuimma"
#elif DirExists("..\\..\\dist\\windows\\SistemaGuimma\\_internal")
  #define MainIsOneDir 1
  #define MainDirSource "..\\..\\dist\\windows\\SistemaGuimma"
#else
  #define MainIsOneDir 0
  #if FileExists("..\\..\\dist\\SistemaGuimma\\SistemaGuimma.exe")
    #define MainExeSource "..\\..\\dist\\SistemaGuimma\\SistemaGuimma.exe"
  #elif FileExists("..\\..\\dist\\windows\\SistemaGuimma.exe")
    #define MainExeSource "..\\..\\dist\\windows\\SistemaGuimma.exe"
  #else
    #define MainExeSource "..\\..\\dist\\SistemaGuimma.exe"
  #endif
#endif

; Configurador (onefile) - prioridade dist\SistemaGuimma
#if FileExists("..\\..\\dist\\SistemaGuimma\\CONFIGURAR_BANCO.exe")
  #define DbConfigSource "..\\..\\dist\\SistemaGuimma\\CONFIGURAR_BANCO.exe"
#elif FileExists("..\\..\\dist\\windows\\CONFIGURAR_BANCO.exe")
  #define DbConfigSource "..\\..\\dist\\windows\\CONFIGURAR_BANCO.exe"
#else
  #define DbConfigSource "..\\..\\dist\\SistemaGuimma\\CONFIGURAR_BANCO.exe"
#endif

; App de licenciamento
#if FileExists("..\\..\\dist\\SistemaGuimmaLicenca.exe")
  #define LicencaSource "..\\..\\dist\\SistemaGuimmaLicenca.exe"
#elif FileExists("..\\..\\dist\\SistemaGuimma\\SistemaGuimmaLicenca.exe")
  #define LicencaSource "..\\..\\dist\\SistemaGuimma\\SistemaGuimmaLicenca.exe"
#else
  #define LicencaSource "..\\..\\dist\\SistemaGuimmaLicenca.exe"
#endif

; Icone do configurador: prioriza icon_config.ico, senao usa configurador.ico gerado no build
#if FileExists("..\\..\\icons\\icon_config.ico")
  #define IconConfigSource "..\\..\\icons\\icon_config.ico"
#elif FileExists("..\\..\\dist\\SistemaGuimma\\configurador.ico")
  #define IconConfigSource "..\\..\\dist\\SistemaGuimma\\configurador.ico"
#elif FileExists("..\\..\\build\\configurador.ico")
  #define IconConfigSource "..\\..\\build\\configurador.ico"
#else
  ; fallback: usa o icone principal
  #define IconConfigSource "..\\..\\icons\\ICONE_SISTEMA.ico"
#endif

[Setup]
AppName={#AppName}
AppVerName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppId={{E5D81A21-CC47-4A3A-9C0F-2D7A6C1D49AA}}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\ICONE_SISTEMA.ico
Compression=lzma2/ultra
SolidCompression=yes
OutputDir=..\\..\\dist
#if ARCH == "x86"
OutputBaseFilename=Sistema_Guimma_Setup_x86
ArchitecturesAllowed=x86
ArchitecturesInstallIn64BitMode=
#else
OutputBaseFilename=Sistema_Guimma_Setup_x64
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
#endif
SetupIconFile=..\\..\\icons\\ICONE_SISTEMA.ico
WizardStyle=modern
WizardResizable=yes
PrivilegesRequired=admin

[Registry]
; Nao gravar versao na lista de programas (zera DisplayVersion)
Root: HKLM; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#SetupSetting('AppId')}_is1"; ValueType: string; ValueName: "DisplayVersion"; ValueData: ""; Check: IsAdminInstallMode; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#SetupSetting('AppId')}_is1"; ValueType: string; ValueName: "DisplayVersion"; ValueData: ""; Check: not IsAdminInstallMode; Flags: uninsdeletevalue

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar icone na area de trabalho"; GroupDescription: "Icones adicionais:"; Flags: unchecked

[Files]
; =========================
; APP PRINCIPAL
; =========================
#if MainIsOneDir == 1
; Copia TUDO do onedir (inclui SistemaGuimma.exe + _internal + dlls/zip)
Source: "{#MainDirSource}\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
; Onefile (exe Ãºnico)
Source: "{#MainExeSource}"; DestDir: "{app}"; DestName: "{#AppExeName}"; Flags: ignoreversion
#endif

; Configurador do banco
Source: "{#DbConfigSource}"; DestDir: "{app}"; DestName: "{#ConfiguradorName}"; Flags: ignoreversion

; App de licenciamento
Source: "{#LicencaSource}"; DestDir: "{app}"; DestName: "{#LicencaName}"; Flags: ignoreversion

; Icones (copiados direto para {app} para uso no Menu/Atalhos)
Source: "..\\..\\icons\\ICONE_SISTEMA.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#IconConfigSource}"; DestDir: "{app}"; DestName: "icon_config.ico"; Flags: ignoreversion

#if FileExists("..\\..\\icons\\icon_config.png")
Source: "..\\..\\icons\\icon_config.png"; DestDir: "{app}"; DestName: "icon_config.png"; Flags: ignoreversion
#endif

; Copia a pasta icons inteira (se existir) para {app}\\icons
#if DirExists("..\\..\\icons")
Source: "..\\..\\icons\\*"; DestDir: "{app}\\icons"; Flags: recursesubdirs createallsubdirs
#endif

; Pastas de dados (mantemos no disco para o app ler direto, se precisar)
#if DirExists("..\\..\\PAGINAS_DO_SISTEMA")
Source: "..\\..\\PAGINAS_DO_SISTEMA\\*"; DestDir: "{app}\\PAGINAS_DO_SISTEMA"; Flags: recursesubdirs createallsubdirs
#endif
#if DirExists("..\\..\\data")
Source: "..\\..\\data\\*"; DestDir: "{app}\\data"; Flags: recursesubdirs createallsubdirs
#endif

[Dirs]
Name: "{app}"
Name: "{userappdata}\\SistemaGuimma"
Name: "{userappdata}\\SistemaGuimma\\config"

[Icons]
; Menu Iniciar
Name: "{group}\\{#AppName}"; Filename: "{app}\\{#AppExeName}"; IconFilename: "{app}\\ICONE_SISTEMA.ico"
Name: "{group}\\Configurar Banco de Dados"; Filename: "{app}\\{#ConfiguradorName}"; IconFilename: "{app}\\icon_config.ico"
Name: "{group}\\Licenciamento Sistema Guimma"; Filename: "{app}\\{#LicencaName}"; IconFilename: "{app}\\ICONE_SISTEMA.ico"
Name: "{group}\\Desinstalar {#AppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\\ICONE_SISTEMA.ico"

; Area de trabalho
Name: "{autodesktop}\\{#AppName}"; Filename: "{app}\\{#AppExeName}"; IconFilename: "{app}\\ICONE_SISTEMA.ico"; Tasks: desktopicon
Name: "{autodesktop}\\Configurar Banco"; Filename: "{app}\\{#ConfiguradorName}"; IconFilename: "{app}\\icon_config.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\\{#ConfiguradorName}"; Description: "Configurar banco de dados agora"; Flags: postinstall runasoriginaluser
Filename: "{app}\\{#LicencaName}"; Parameters: "--install-autostart"; Flags: runhidden runasoriginaluser
Filename: "{app}\\{#AppExeName}"; Description: "Executar {#AppName}"; Flags: postinstall nowait runasoriginaluser unchecked
