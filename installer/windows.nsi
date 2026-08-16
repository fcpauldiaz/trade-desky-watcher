Unicode True
!ifndef VERSION
  !define VERSION "0.0.0"
!endif
Name "Trade Desky Watcher"
OutFile "..\dist\TradeDeskyWatcher-${VERSION}-setup.exe"
InstallDir "$LOCALAPPDATA\Programs\TradeDeskyWatcher"
RequestExecutionLevel user
SilentInstall silent

Section "Install"
  SetOutPath $INSTDIR
  File /r "..\dist\TradeDeskyWatcher\*.*"
  CreateShortCut "$SMPROGRAMS\Trade Desky Watcher.lnk" "$INSTDIR\TradeDeskyWatcher.exe"
  CreateShortCut "$DESKTOP\Trade Desky Watcher.lnk" "$INSTDIR\TradeDeskyWatcher.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  Exec '"$INSTDIR\TradeDeskyWatcher.exe"'
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\Trade Desky Watcher.lnk"
  Delete "$DESKTOP\Trade Desky Watcher.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
