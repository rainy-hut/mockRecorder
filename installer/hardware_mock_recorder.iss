[Setup]
AppName=Hardware Mock Recorder
AppVersion=1.0.0
DefaultDirName={autopf}\HardwareMockRecorder
DefaultGroupName=Hardware Mock Recorder
OutputBaseFilename=HardwareMockRecorderSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\HardwareMockRecorder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Hardware Mock Recorder"; Filename: "{app}\HardwareMockRecorder.exe"
Name: "{commondesktop}\Hardware Mock Recorder"; Filename: "{app}\HardwareMockRecorder.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
