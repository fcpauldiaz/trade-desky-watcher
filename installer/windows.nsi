Unicode True
!ifndef VERSION
  !define VERSION "0.0.0"
!endif

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"

Var Dialog
Var HWNDLaunch
Var LaunchApp

Name "Trade Desky Watcher ${VERSION}"
OutFile "..\dist\TradeDeskyWatcher-${VERSION}-setup.exe"
InstallDir "$LOCALAPPDATA\Programs\TradeDeskyWatcher"
RequestExecutionLevel user
ShowInstDetails show

!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\icon.ico"
!define MUI_UNICON "..\assets\icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "..\assets\installer-header.bmp"
!define MUI_HEADERIMAGE_RIGHT
!define MUI_WELCOMEFINISHPAGE_BITMAP "..\assets\installer-welcome.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "..\assets\installer-welcome.bmp"
!define MUI_WELCOMEPAGE_TITLE "Trade Desky Watcher Setup ${VERSION}"
!define MUI_WELCOMEPAGE_TEXT "This installs Trade Desky Watcher for Trade Desky — the desktop app that forwards alert notifications to your account.$\r$\n$\r$\nThere is no main window. After setup, look for the Trade Desky icon (lime arrow on dark tile) in the Windows notification area near the clock.$\r$\n$\r$\nInstaller version ${VERSION}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
Page custom FinishPageCreate FinishPageLeave
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "Trade Desky Watcher"
VIAddVersionKey "CompanyName" "Chapi Labs"
VIAddVersionKey "LegalCopyright" "Copyright 2026 Chapi Labs"
VIAddVersionKey "FileDescription" "Trade Desky Watcher"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"

Function FinishPageCreate
  !insertmacro MUI_HEADER_TEXT "Trade Desky" "Watcher is ready — find it in the notification area."

  nsDialogs::Create 1018
  Pop $Dialog
  ${If} $Dialog == error
    Abort
  ${EndIf}

  ${NSD_CreateLabel} 0 0 100% 72u "Trade Desky Watcher does not open a regular window.$\r$\n$\r$\n1. Look for the Trade Desky icon (lime arrow on dark tile) in the notification area (bottom-right).$\r$\n2. If you do not see it, click the ^ chevron to show hidden icons.$\r$\n3. Right-click the icon → Account → Sign in… with your Trade Desky account.$\r$\n$\r$\nStart Menu and Desktop shortcuts use the same Trade Desky branding."
  Pop $0

  ${NSD_CreateCheckbox} 0 80u 100% 12u "Launch Trade Desky Watcher now"
  Pop $HWNDLaunch
  ${NSD_Check} $HWNDLaunch

  nsDialogs::Show
FunctionEnd

Function FinishPageLeave
  ${NSD_GetState} $HWNDLaunch $LaunchApp
  ${If} $LaunchApp == ${BST_CHECKED}
    Exec '"$INSTDIR\TradeDeskyWatcher.exe"'
  ${EndIf}
FunctionEnd

Section "Install"
  SetOutPath $INSTDIR
  File /r "..\dist\TradeDeskyWatcher\*.*"
  CreateDirectory "$SMPROGRAMS\Trade Desky Watcher"
  CreateShortCut "$SMPROGRAMS\Trade Desky Watcher\Trade Desky Watcher.lnk" "$INSTDIR\TradeDeskyWatcher.exe"
  CreateShortCut "$DESKTOP\Trade Desky Watcher.lnk" "$INSTDIR\TradeDeskyWatcher.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\Trade Desky Watcher\Trade Desky Watcher.lnk"
  RMDir "$SMPROGRAMS\Trade Desky Watcher"
  Delete "$DESKTOP\Trade Desky Watcher.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
