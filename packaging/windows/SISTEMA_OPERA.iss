#define AppName "SISTEMA OPERA"
#define AppVersion "1.0.0"
#define AppPublisher "Opera Fashion"
#define AppExeName "SistemaOpera.exe"
#define IconPath "..\\..\\src\\PAGINAS_DO_SISTEMA\\ICONE_SISTEMA.ico"

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
#if FileExists(IconPath)
SetupIconFile={#IconPath}
#endif

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

[Code]
var
  DbConfigPage: TInputQueryWizardPage;
  AutoDetectPortsCheck: TCheckBox;

function JsonEscape(const Value: string): string;
begin
  Result := StringReplace(Value, '\', '\\', [rfReplaceAll]);
  Result := StringReplace(Result, '"', '\"', [rfReplaceAll]);
end;

function GetDbConfigPath(): string;
begin
  Result := ExpandConstant('{userappdata}\SistemaOpera\config.json');
end;

procedure InitializeWizard;
begin
  DbConfigPage :=
    CreateInputQueryPage(
      wpSelectDir,
      'Configuração do Banco de Dados',
      'Informe os dados para conectar o sistema ao banco.',
      'Essas informações serão gravadas em ' + GetDbConfigPath() + ' e podem ser alteradas depois.'
    );

  DbConfigPage.Add('IP/Host do Banco:', False);
  DbConfigPage.Add('Porta:', False);
  DbConfigPage.Add('Nome do Banco:', False);
  DbConfigPage.Add('Usuário:', False);
  DbConfigPage.Add('Senha:', True);
  DbConfigPage.Add('Schema:', False);

  DbConfigPage.Values[0] := 'localhost';
  DbConfigPage.Values[1] := '5432';
  DbConfigPage.Values[2] := 'BANCO_OPERA';
  DbConfigPage.Values[3] := 'postgres';
  DbConfigPage.Values[4] := '';
  DbConfigPage.Values[5] := 'opera';

  AutoDetectPortsCheck := TCheckBox.Create(DbConfigPage.Surface);
  AutoDetectPortsCheck.Parent := DbConfigPage.Surface;
  AutoDetectPortsCheck.Caption := 'Detectar porta automaticamente (se disponível)';
  AutoDetectPortsCheck.Checked := True;
  AutoDetectPortsCheck.Top := DbConfigPage.Edits[5].Top + DbConfigPage.Edits[5].Height + ScaleY(10);
  AutoDetectPortsCheck.Left := DbConfigPage.Edits[5].Left;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  PortValue: Integer;
begin
  Result := True;
  if CurPageID = DbConfigPage.ID then
  begin
    if Trim(DbConfigPage.Values[0]) = '' then
    begin
      MsgBox('Informe o IP/Host do banco.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if Trim(DbConfigPage.Values[1]) = '' then
    begin
      MsgBox('Informe a porta do banco.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if not TryStrToInt(Trim(DbConfigPage.Values[1]), PortValue) then
    begin
      MsgBox('A porta precisa ser numérica.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if Trim(DbConfigPage.Values[2]) = '' then
    begin
      MsgBox('Informe o nome do banco.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if Trim(DbConfigPage.Values[3]) = '' then
    begin
      MsgBox('Informe o usuário do banco.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

procedure WriteDbConfigFile;
var
  ConfigPath: string;
  ConfigDir: string;
  HostValue: string;
  PortValue: string;
  DbNameValue: string;
  UserValue: string;
  PasswordValue: string;
  SchemaValue: string;
  AutoDetectValue: string;
  JsonContent: string;
begin
  ConfigPath := GetDbConfigPath();
  ConfigDir := ExtractFileDir(ConfigPath);
  ForceDirectories(ConfigDir);

  HostValue := Trim(DbConfigPage.Values[0]);
  PortValue := Trim(DbConfigPage.Values[1]);
  DbNameValue := Trim(DbConfigPage.Values[2]);
  UserValue := Trim(DbConfigPage.Values[3]);
  PasswordValue := DbConfigPage.Values[4];
  SchemaValue := Trim(DbConfigPage.Values[5]);

  if AutoDetectPortsCheck.Checked then
    AutoDetectValue := 'true'
  else
    AutoDetectValue := 'false';

  JsonContent :=
    '{'#13#10 +
    '  "schema": "' + JsonEscape(SchemaValue) + '",'#13#10 +
    '  "appname": "OPERA_APP",'#13#10 +
    '  "defaults": {'#13#10 +
    '    "dbname": "' + JsonEscape(DbNameValue) + '",'#13#10 +
    '    "user": "' + JsonEscape(UserValue) + '",'#13#10 +
    '    "password": "' + JsonEscape(PasswordValue) + '"'#13#10 +
    '  },'#13#10 +
    '  "hosts": ["' + JsonEscape(HostValue) + '"],'#13#10 +
    '  "ports": [' + PortValue + '],'#13#10 +
    '  "connect_timeout": 10,'#13#10 +
    '  "auto_detect_ports": ' + AutoDetectValue + ','#13#10 +
    '  "fallback_to_postgres": true'#13#10 +
    '}'#13#10;

  SaveStringToFile(ConfigPath, JsonContent, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    WriteDbConfigFile;
  end;
end;
