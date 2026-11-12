; Inno Setup script - run build_exe.bat first so dist\MatePadPDF.exe exists.
; Then open this file in Inno Setup (https://jrsoftware.org/isdl.php) and press Compile (Ctrl+F9).
; Result: installer\MatePadPDF_Setup.exe

[Setup]
AppName=MatePad PDF Converter
AppVersion=1.0
DefaultDirName={autopf}\MatePadPDF
DefaultGroupName=MatePad PDF Converter
OutputDir=installer
OutputBaseFilename=MatePadPDF_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\MatePadPDF.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\MatePadPDF.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MatePad PDF Converter"; Filename: "{app}\MatePadPDF.exe"
Name: "{autodesktop}\MatePad PDF Converter"; Filename: "{app}\MatePadPDF.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MatePadPDF.exe"; Description: "Launch MatePad PDF Converter"; Flags: nowait postinstall skipifsilent
