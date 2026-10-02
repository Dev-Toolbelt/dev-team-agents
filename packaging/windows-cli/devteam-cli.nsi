; devteam-cli.nsi — per-user Windows installer for the devteam CLI (ADR-0028).
;
; Built by build.py, which stages the files and passes:
;   VERSION  the framework/CLI version (X.Y.Z)
;   ARCH     x64 | arm64 — which embedded Python and launcher the stage holds
;   STAGE    the staged tree: python\ cli\ launcher\ payload\ postinstall.py
;   OUTFILE  the installer to write
;
; Copies files only. PATH, the launcher and the store install are postinstall.py's job,
; run with the Python this installer places. The uninstaller never touches the store.

Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define PRODUCT "devteam CLI"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\DevToolbelt.Devteam"
; What postinstall.py's check-git returns when no Git Bash is found.
!define GIT_MISSING 10

Name "${PRODUCT} ${VERSION}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\devteam"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT}"
VIAddVersionKey "FileDescription" "${PRODUCT} installer (${ARCH})"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "CompanyName" "dev-team-agents contributors"
VIAddVersionKey "LegalCopyright" "MIT License"

!define MUI_WELCOMEPAGE_TITLE "${PRODUCT} ${VERSION}"
!define MUI_WELCOMEPAGE_TEXT "This installs the devteam command-line tool for your user account, with its own Python — nothing else on this computer is changed, and no administrator rights are needed.$\r$\n$\r$\nIf Git for Windows is missing, you will be offered to install it: the hooks of dev-team-agents run in Git Bash.$\r$\n$\r$\nClose the Dev Team Agents app before upgrading."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TEXT "devteam is installed. Open a new terminal to use it, and reopen the Dev Team Agents app if it was running."
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "PortugueseBR"

; The directories this installer owns outright inside $INSTDIR.
!macro OWNED_DIRS
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\cli"
  RMDir /r "$INSTDIR\launcher"
  RMDir /r "$INSTDIR\payload"
!macroend

Function .onInit
  ; `/D=` (winget's --location) may name any directory. Installing into a dedicated
  ; `devteam` folder under it keeps the uninstaller's deletions inside what it created.
  ${GetFileName} "$INSTDIR" $0
  ${If} $0 != "devteam"
    StrCpy $INSTDIR "$INSTDIR\devteam"
  ${EndIf}
FunctionEnd

Section "devteam"
  SetOutPath "$INSTDIR"
  ; A loaded python3.dll cannot be opened for writing: devteam (or the app's watchers) is
  ; running from this install, and replacing it now would leave half an install behind.
  ${If} ${FileExists} "$INSTDIR\python\python3.dll"
    in_use_check:
    ClearErrors
    FileOpen $0 "$INSTDIR\python\python3.dll" a
    ${If} ${Errors}
      MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "devteam is running from this install. Close the Dev Team Agents app and any terminal running devteam, then retry." /SD IDCANCEL IDRETRY in_use_check
      SetErrorLevel 3
      Abort "devteam is in use; nothing was changed."
    ${EndIf}
    FileClose $0
  ${EndIf}
  ; Directories this installer owns outright are replaced, so an upgrade leaves no stale
  ; module behind. bin\ is rewritten by postinstall.py.
  !insertmacro OWNED_DIRS
  File /r "${STAGE}\python"
  File /r "${STAGE}\cli"
  File /r "${STAGE}\launcher"
  File /r "${STAGE}\payload"
  File "${STAGE}\postinstall.py"
  WriteUninstaller "$INSTDIR\uninstall.exe"

  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${PRODUCT}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "dev-team-agents contributors"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1

  DetailPrint "Looking for Git Bash..."
  nsExec::ExecToLog '"$INSTDIR\python\python.exe" "$INSTDIR\postinstall.py" check-git --instdir "$INSTDIR"'
  Pop $0
  ${If} $0 == ${GIT_MISSING}
    ; A silent install is winget's: its manifest declares Git.Git as a dependency instead.
    IfSilent git_done
    MessageBox MB_YESNO|MB_ICONQUESTION "Git for Windows was not found. The dev-team-agents hooks run in Git Bash.$\r$\n$\r$\nInstall it now with winget (for your user only)? A window opens and winget asks you to accept the Git license." IDNO git_skipped
    ; By absolute path: a bare `winget` is searched for in the installer's own directory
    ; first, where a planted winget.exe beside a downloaded installer would run.
    StrCpy $2 "$LOCALAPPDATA\Microsoft\WindowsApps\winget.exe"
    ClearErrors
    ${If} ${FileExists} $2
      ExecWait '"$2" install --id Git.Git --exact --scope user --source winget' $1
    ${Else}
      SetErrors
    ${EndIf}
    ${If} ${Errors}
      MessageBox MB_OK|MB_ICONINFORMATION "winget is not available on this computer. Install Git for Windows from https://git-scm.com/download/win and the hooks will find it." /SD IDOK
    ${ElseIf} $1 != 0
      DetailPrint "winget exited with $1; Git for Windows may not be installed."
    ${EndIf}
    Goto git_done
    git_skipped:
      DetailPrint "Git for Windows skipped. Install it later from https://git-scm.com/download/win"
    git_done:
  ${EndIf}

  DetailPrint "Setting up devteam..."
  nsExec::ExecToLog '"$INSTDIR\python\python.exe" "$INSTDIR\postinstall.py" install --instdir "$INSTDIR"'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_OK|MB_ICONEXCLAMATION "devteam was copied, but setting it up failed (exit $0). The details are in this window's log." /SD IDOK
    SetErrorLevel 2
  ${EndIf}
SectionEnd

Section "Uninstall"
  nsExec::ExecToLog '"$INSTDIR\python\python.exe" "$INSTDIR\postinstall.py" uninstall --instdir "$INSTDIR"'
  Pop $0
  ; Only what this installer wrote, then the directory itself if that left it empty —
  ; never `RMDir /r "$INSTDIR"`, which a `/D=` naming a shared folder would turn into
  ; deleting it. The store (%LOCALAPPDATA%\dev-team-agents, %APPDATA%\dev-team-agents) is
  ; the user's and survives, as with every channel.
  !insertmacro OWNED_DIRS
  RMDir /r "$INSTDIR\bin"
  Delete "$INSTDIR\postinstall.py"
  Delete "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
SectionEnd
