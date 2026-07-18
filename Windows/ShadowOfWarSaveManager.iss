; Inno Setup script for Shadow of War Save Manager
;
; This wraps the already-built ShadowOfWarSaveManager.exe (from build_exe.bat)
; into a proper Windows installer with a Start Menu entry, optional Desktop
; icon, and an uninstaller in "Add or Remove Programs".
;
; HOW TO USE:
;   1. Install Inno Setup (free): https://jrsoftware.org/isinfo.php
;   2. Make sure dist\ShadowOfWarSaveManager.exe already exists (run
;      build_exe.bat first if it doesn't) and icon.ico is in this folder.
;   3. Open this file in Inno Setup (double-click it, or "Open" from the
;      Inno Setup Compiler), then click Build > Compile (or press F9/Ctrl+F9).
;   4. The finished installer will be in the "Output" folder:
;      Output\ShadowOfWarSaveManager_Setup.exe

#define MyAppName "Shadow of War Save Manager"
#define MyAppVersion "1.0.0"
#define MyAppExeName "ShadowOfWarSaveManager.exe"

[Setup]
AppId={{B6C8B6A0-6E6E-4C7A-9F0D-SHADOWOFWAR1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=ShadowOfWarSaveManager_Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
