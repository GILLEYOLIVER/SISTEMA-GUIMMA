#define AppName "SISTEMA OPERA"
#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#define AppPublisher "Opera Fashion"
#define AppExeName "SistemaOpera.exe"

; =========================
; Personalizacao (Windows)
; =========================
#define SetupIco "..\\ICONE_SISTEMA.ico"
#define WizBigBmp "..\\wizard_big.bmp"
#define WizSmallBmp "..\\wizard_small.bmp"

#ifndef OutputDir
#define OutputDir "..\\..\\dist"
#endif
#ifndef OutputBaseFilename
#define OutputBaseFilename "SistemaOpera_Setup"
#endif

; =========================
; Configurador do banco (CustomTkinter) - DETECCAO NO BUILD
; =========================
#define DbHelperExePath1 "..\\..\\dist\\SistemaOpera\\CONFIGURAR_BANCO.exe"
#define DbHelperExePath2 "..\\..\\dist\\SistemaOpera\\SETUP_BANCO.exe"

#if FileExists(DbHelperExePath1)
  #define DbHelperExePath DbHelperExePath1
  #define DbHelperExeName "CONFIGURAR_BANCO.exe"
  #define HAS_DB_HELPER
#elif FileExists(DbHelperExePath2)
  #define DbHelperExePath DbHelperExePath2
  #define DbHelperExeName "SETUP_BANCO.exe"
  #define HAS_DB_HELPER
#else
  #define DbHelperExeName ""
#endif

[Setup]
AppId={{E5D81A21-CC47-4A3A-9C0F-2D7A6C1D49AA}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}

OutputBaseFilename={#OutputBaseFilename}
OutputDir={#OutputDir}

Compression=lzma
SolidCompression=yes
WizardStyle=modern

WizardResizable=yes
WizardSizePercent=135,135

#if FileExists(SetupIco)
SetupIconFile={#SetupIco}
#endif

#if FileExists(WizBigBmp)
WizardImageFile={#WizBigBmp}
#endif
#if FileExists(WizSmallBmp)
WizardSmallImageFile={#WizSmallBmp}
#endif

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar icone na area de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
; App principal (toda a pasta dist\SistemaOpera)
Source: "..\\..\\dist\\SistemaOpera\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\\..\\dist\\SistemaOpera\\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Configurador do banco:
; 1) instala no {app} para o usuario poder abrir depois
; 2) extrai uma copia temporaria no {tmp} para rodar DURANTE a fase do instalador (antes da instalacao efetiva)
#ifdef HAS_DB_HELPER
Source: "{#DbHelperExePath}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#DbHelperExePath}"; DestName: "CONFIGURAR_BANCO_TMP.exe"; Flags: dontcopy
#endif

[Dirs]
Name: "{userappdata}\\SistemaOpera"
Name: "{userappdata}\\SistemaOpera\\config"
Name: "{userappdata}\\SistemaOpera\\logs"

[Icons]
Name: "{group}\\{#AppName}"; Filename: "{app}\\{#AppExeName}"
Name: "{commondesktop}\\{#AppName}"; Filename: "{app}\\{#AppExeName}"; Tasks: desktopicon
#ifdef HAS_DB_HELPER
Name: "{group}\\Configurar Banco de Dados"; Filename: "{app}\\{#DbHelperExeName}"
#endif

[Run]
Filename: "{app}\\{#AppExeName}"; Description: "Executar {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DbPhasePage: TWizardPage;
  DbInfoLabel: TNewStaticText;
  DbHelperOk: Boolean;
  DbAutoLaunchedOnce: Boolean;

procedure ResizeWizardBigger();
begin
  try
    WizardForm.ClientWidth := ScaleX(920);
    WizardForm.ClientHeight := ScaleY(600);
  except
  end;
end;

function HasDbHelper(): Boolean;
begin
  Result := False;
  {$ifdef HAS_DB_HELPER}
    Result := True;
  {$endif}
end;

function GetDbHelperTempExe(): string;
begin
  Result := ExpandConstant('{tmp}\CONFIGURAR_BANCO_TMP.exe');
end;

procedure LaunchDbHelperOrWarn();
var
  exePath: string;
  rc: Integer;
begin
  if not HasDbHelper() then
  begin
    DbHelperOk := True;
    DbInfoLabel.Caption :=
      'O configurador do banco nao foi incluido neste build.' + #13#10 +
      'A instalacao vai continuar. Depois, use "Configurar Banco de Dados" no menu Iniciar.';
    Exit;
  end;

  try
    ExtractTemporaryFile('CONFIGURAR_BANCO_TMP.exe');
  except
    DbHelperOk := False;
    DbInfoLabel.Caption := 'Nao foi possivel extrair o configurador do banco.';
    Exit;
  end;

  exePath := GetDbHelperTempExe();
  if not FileExists(exePath) then
  begin
    DbHelperOk := False;
    DbInfoLabel.Caption := 'O configurador do banco nao foi encontrado no temporario.';
    Exit;
  end;

  DbInfoLabel.Caption := 'Abrindo configurador do banco...';
  if Exec(exePath, '', '', SW_SHOW, ewWaitUntilTerminated, rc) then
  begin
    if rc = 0 then
    begin
      DbHelperOk := True;
      DbInfoLabel.Caption := 'OK! Banco configurado. Clique em Avancar para continuar.';
    end
    else
    begin
      DbHelperOk := False;
      DbInfoLabel.Caption := 'Fechado sem concluir. Clique em Avancar para abrir novamente.';
    end;
  end
  else
  begin
    DbHelperOk := False;
    DbInfoLabel.Caption := 'Nao foi possivel abrir o configurador. Clique em Avancar para tentar novamente.';
  end;
end;

procedure InitializeWizard;
begin
  ResizeWizardBigger();

  DbPhasePage := CreateCustomPage(
    wpSelectDir,
    'Configuracao do Banco de Dados',
    'Esta etapa faz parte da instalacao do SISTEMA OPERA.'
  );

  DbInfoLabel := TNewStaticText.Create(WizardForm);
  DbInfoLabel.Parent := DbPhasePage.Surface;
  DbInfoLabel.Left := ScaleX(0);
  DbInfoLabel.Top := ScaleY(0);
  DbInfoLabel.Width := DbPhasePage.SurfaceWidth;
  DbInfoLabel.Height := ScaleY(220);
  DbInfoLabel.AutoSize := False;
  DbInfoLabel.WordWrap := True;
  DbInfoLabel.Caption := 'Preparando configurador do banco...';

  DbHelperOk := False;
  DbAutoLaunchedOnce := False;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = DbPhasePage.ID) and (not DbAutoLaunchedOnce) then
  begin
    DbAutoLaunchedOnce := True;
    LaunchDbHelperOrWarn();
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = DbPhasePage.ID then
  begin
    if HasDbHelper() and (not DbHelperOk) then
    begin
      MsgBox('Finalize a configuracao do banco para continuar.', mbInformation, MB_OK);
      LaunchDbHelperOrWarn();
      Result := DbHelperOk;
    end;
  end;
end;
