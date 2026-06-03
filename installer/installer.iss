; Lumos Home Windows Installer
; Built with Inno Setup 6

#define MyAppName "Lumos Home"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Lumos Home"
#define MyAppExeName "LumosHome.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=LumosHome-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: checked

[Files]
; Main application (PyInstaller --onedir output)
Source: "..\backend\dist\LumosHome\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; External tools (deployed at app root, not inside _internal)
Source: "redist\ffmpeg.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "redist\nmap\*"; DestDir: "{app}\nmap"; Flags: ignoreversion recursesubdirs createallsubdirs
; Npcap installer (temp, for silent install)
Source: "redist\npcap.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Silent Npcap installation
Filename: "{tmp}\npcap.exe"; Parameters: "/S"; StatusMsg: "正在安装 Npcap..."; Flags: waituntilterminated runhidden

[UninstallDelete]
; Do NOT delete data directory — preserve user data

[Code]
var
  DataDirPage: TInputDirWizardPage;

function GetFirstNonCDrive: String;
var
  Drive: Char;
begin
  for Drive := 'D' to 'Z' do
  begin
    if DirExists(Drive + ':\') then
    begin
      Result := Drive + ':\LumosHome\data';
      Exit;
    end;
  end;
  Result := 'C:\LumosHome\data';
end;

procedure InitializeWizard;
begin
  DataDirPage := CreateInputDirPage(
    wpSelectDir,
    '选择数据目录',
    '程序运行时的数据将存储在此目录（数据库、录像、日志）',
    '请选择数据目录：',
    False,
    ''
  );
  DataDirPage.Add('');
  DataDirPage.Values[0] := GetFirstNonCDrive;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DataDirPage.ID then
  begin
    if DataDirPage.Values[0] = '' then
    begin
      MsgBox('请输入数据目录路径', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure WriteAppCfg;
var
  CfgPath: String;
  CfgContent: TArrayOfString;
begin
  CfgPath := ExpandConstant('{app}\app.cfg');
  SetArrayLength(CfgContent, 2);
  CfgContent[0] := '[paths]';
  CfgContent[1] := 'data_dir = ' + DataDirPage.Values[0];
  SaveStringsToFile(CfgPath, CfgContent, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    WriteAppCfg;
    ForceDirectories(DataDirPage.Values[0]);
  end;
end;
