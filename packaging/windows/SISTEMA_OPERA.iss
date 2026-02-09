#define AppName "SISTEMA OPERA"
#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#define AppPublisher "Opera Fashion"
#define AppExeName "SistemaOpera.exe"
#define IconPath "..\\..\\src\\PAGINAS_DO_SISTEMA\\ICONE_SISTEMA.ico"
#ifndef OutputDir
#define OutputDir "..\\.."
#endif
#ifndef OutputBaseFilename
#define OutputBaseFilename "Instalador_{#AppName}"
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
  LocalDbCheck: TCheckBox;
  TestConnectionButton: TButton;
  DetectPortButton: TButton;

procedure LocalDbCheckClick(Sender: TObject);
procedure TestConnectionClick(Sender: TObject);
procedure DetectPortClick(Sender: TObject);

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

  LocalDbCheck := TCheckBox.Create(DbConfigPage.Surface);
  LocalDbCheck.Parent := DbConfigPage.Surface;
  LocalDbCheck.Caption := 'Banco local (localhost)';
  LocalDbCheck.Checked := True;
  LocalDbCheck.Top := AutoDetectPortsCheck.Top + AutoDetectPortsCheck.Height + ScaleY(6);
  LocalDbCheck.Left := AutoDetectPortsCheck.Left;
  LocalDbCheck.OnClick := @LocalDbCheckClick;

  TestConnectionButton := TButton.Create(DbConfigPage.Surface);
  TestConnectionButton.Parent := DbConfigPage.Surface;
  TestConnectionButton.Caption := 'Testar conexão';
  TestConnectionButton.Top := LocalDbCheck.Top + LocalDbCheck.Height + ScaleY(10);
  TestConnectionButton.Left := LocalDbCheck.Left;
  TestConnectionButton.OnClick := @TestConnectionClick;

  DetectPortButton := TButton.Create(DbConfigPage.Surface);
  DetectPortButton.Parent := DbConfigPage.Surface;
  DetectPortButton.Caption := 'Buscar porta';
  DetectPortButton.Top := TestConnectionButton.Top;
  DetectPortButton.Left := TestConnectionButton.Left + TestConnectionButton.Width + ScaleX(12);
  DetectPortButton.OnClick := @DetectPortClick;

  LocalDbCheckClick(LocalDbCheck);
end;

procedure LocalDbCheckClick(Sender: TObject);
begin
  if LocalDbCheck.Checked then
  begin
    DbConfigPage.Values[0] := 'localhost';
    if Trim(DbConfigPage.Values[1]) = '' then
      DbConfigPage.Values[1] := '5432';
  end;

  DbConfigPage.Edits[0].Enabled := not LocalDbCheck.Checked;
end;

function TestHostPort(const HostValue: string; const PortValue: string): Boolean;
var
  ResultCode: Integer;
  Command: string;
begin
  Command :=
    '-NoProfile -ExecutionPolicy Bypass -Command "if (Test-NetConnection -ComputerName ''' +
    HostValue + ''' -Port ' + PortValue + ' -InformationLevel Quiet) { exit 0 } else { exit 1 }"';

  if Exec('powershell.exe', Command, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := ResultCode = 0
  else
    Result := False;
end;

function PopNextToken(var ListValue: string): string;
var
  CommaPos: Integer;
begin
  CommaPos := Pos(',', ListValue);
  if CommaPos = 0 then
  begin
    Result := ListValue;
    ListValue := '';
  end
  else
  begin
    Result := Copy(ListValue, 1, CommaPos - 1);
    ListValue := Copy(ListValue, CommaPos + 1, Length(ListValue) - CommaPos);
  end;
end;

function DetectPortForHost(const HostValue: string): string;
var
  PortsToTry: string;
  CurrentPort: string;
begin
  Result := '';
  PortsToTry := '5432,5433,5434,5435,5436';

  while PortsToTry <> '' do
  begin
    CurrentPort := PopNextToken(PortsToTry);
    if TestHostPort(HostValue, CurrentPort) then
    begin
      Result := CurrentPort;
      Exit;
    end;
  end;
end;

procedure TestConnectionClick(Sender: TObject);
var
  HostValue: string;
  PortValue: string;
begin
  HostValue := Trim(DbConfigPage.Values[0]);
  PortValue := Trim(DbConfigPage.Values[1]);

  if (HostValue = '') or (PortValue = '') then
  begin
    MsgBox('Informe IP/Host e porta antes de testar.', mbError, MB_OK);
    Exit;
  end;

  if TestHostPort(HostValue, PortValue) then
    MsgBox('Conexão OK: o banco respondeu no host/porta informados.', mbInformation, MB_OK)
  else
    MsgBox('Não foi possível conectar ao banco nesse host/porta.', mbError, MB_OK);
end;

procedure DetectPortClick(Sender: TObject);
var
  HostValue: string;
  DetectedPort: string;
begin
  HostValue := Trim(DbConfigPage.Values[0]);

  if HostValue = '' then
  begin
    MsgBox('Informe o IP/Host do banco antes de buscar a porta.', mbError, MB_OK);
    Exit;
  end;

  DetectedPort := DetectPortForHost(HostValue);
  if DetectedPort <> '' then
  begin
    DbConfigPage.Values[1] := DetectedPort;
    MsgBox('Porta detectada: ' + DetectedPort, mbInformation, MB_OK);
  end
  else
    MsgBox('Não foi possível detectar uma porta aberta para o banco.', mbError, MB_OK);
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
      if AutoDetectPortsCheck.Checked then
      begin
        DbConfigPage.Values[1] := DetectPortForHost(Trim(DbConfigPage.Values[0]));
        if Trim(DbConfigPage.Values[1]) = '' then
        begin
          MsgBox('Não foi possível detectar a porta do banco. Informe manualmente.', mbError, MB_OK);
          Result := False;
          Exit;
        end;
      end
      else
      begin
        MsgBox('Informe a porta do banco.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
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
