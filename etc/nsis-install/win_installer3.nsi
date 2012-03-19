;NSIS Modern User Interface version 1.65
 
!define MUI_PRODUCT "gmvault"
!define MUI_VERSION "1.2.3.4"
 
!include "MUI.nsh"
 
;--------------------------------
;Configuration
 
  ;General
  OutFile "Setup.exe"
 
  AllowRootDirInstall true
 
;--------------------------------
;Modern UI Configuration
 
  !define MUI_WELCOMEPAGE
    !define MUI_SPECIALBITMAP "wizard01.bmp"
  !define MUI_CUSTOMPAGECOMMANDS
  !define MUI_COMPONENTSPAGE
    !define MUI_COMPONENTSPAGE_NODESC
    !define MUI_HEADERBITMAP "LT-Header.bmp"
 
;  !define MUI_ICON "icon.ico"
  !define MUI_DIRECTORYPAGE
;  !define MUI_CUSTOMFUNCTION_COMPONENTS_LEAVE ComponentPost
  !define MUI_CUSTOMFUNCTION_DIRECTORY_PRE DirectoryPre
  !define MUI_CUSTOMFUNCTION_DIRECTORY_SHOW DirectoryShow
  !define MUI_CUSTOMFUNCTION_DIRECTORY_LEAVE DirectoryLeave
 
  !define MUI_FINISHPAGE
    !define MUI_FINISHPAGE_RUN "$2\Harbinger.exe"
    !define MUI_FINISHPAGE_NOREBOOTSUPPORT
 
  !define MUI_ABORTWARNING
 
;--------------------------------
;Pages
 
  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES
  !insertmacro MUI_PAGE_FINISH
 
;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"
 
;--------------------------------
;Reserve Files
 
;Things that need to be extracted on first (keep these lines before any File command!)
;Only useful for BZIP2 compression
;  !insertmacro MUI_RESERVEFILE_WELCOMEFINISHPAGE
 
;--------------------------------
;Installer Types
 
  InstType "Full (Inc. Shortcuts)"
  InstType "Simple (No Shortcuts)"
 
;--------------------------------
;Installer Sections
 
Section "Program Files"
  SectionIn 1 2 RO
  SetOutPath "$2"
  ;-------------------------------------
  ;Your installer instructions go here
  ;-------------------------------------
 
;  File /oname=Harbinger.exe "Harbinger2003s.exe"
  IfFileExists "$2\h2003SE.opt" OptionsOK          ;If Options exist DON'T overwrite
;    File "h2003se.opt"
;    WriteINIStr "$2\h2003se.opt" "Main" "Data" $3  ;Write DataPath to config file
OptionsOK:
  CreateDirectory "$3"
SectionEnd
 
SubSection /E "Shortcuts"
  Section "Desktop"
    SectionIn 1
    SetOutPath "$2"
    SetShellVarContext all
    CreateShortCut "$DESKTOP\Harbinger 2003 Standard Edition.lnk" "$2\Harbinger.exe"
  SectionEnd
 
  Section "Start Menu"
    SectionIn 1
    SetOutPath "$2"
    SetShellVarContext all
    CreateDirectory "$SMPROGRAMS\Harbinger"
    CreateShortCut "$SMPROGRAMS\Harbinger\Harbinger 2003 Standard Edition.lnk" "$2\Harbinger.exe"
  SectionEnd
SubSectionEnd
 
;--------------------------------
;Installer Functions
 
Function .onInit
; Must set $INSTDIR here to avoid adding ${MUI_PRODUCT} to the end of the
; path when user selects a new directory using the 'Browse' button.
  StrCpy $INSTDIR "$PROGRAMFILES\${MUI_PRODUCT}"
FunctionEnd
 
 
Function ComponentPost
  StrCpy $9 "0"
FunctionEnd
 
Function DirectoryPre
  StrCmp $9 "0" OK
    ;Skip 2nd (Data) Directory Page if Options file Exists
    IfFileExists "$2\h2003SE.opt" "" OK
      Abort
OK:
FunctionEnd
 
 
Function DirectoryShow
  StrCmp $9 "0" AppDirectoryPage
;  StrCmp $9 "1" DataDirectoryPage
 
AppDirectoryPage:
  StrCpy $9 "1"
  !insertmacro MUI_INNERDIALOG_TEXT 1041 "Destination Folder"
  !insertmacro MUI_INNERDIALOG_TEXT 1019 "$PROGRAMFILES\${MUI_PRODUCT}\"
  !insertmacro MUI_INNERDIALOG_TEXT 1006 "Setup will install ${MUI_PRODUCT} in the following folder.$\r$\n$\r$\nTo install in a different folder, click Browse and select another folder. Click Next to continue."
  Goto EndDirectoryShow
 
DataDirectoryPage:
  StrCpy $9 "2"
  !insertmacro MUI_HEADER_TEXT "Choose Data Location" "Choose the folder in which to install ${MUI_PRODUCT} - Data Files."
  !insertmacro MUI_INNERDIALOG_TEXT 1041 "Data Destination Folder"
  !insertmacro MUI_INNERDIALOG_TEXT 1019 "$INSTDIR\Data\"
  !insertmacro MUI_INNERDIALOG_TEXT 1006 "Setup will install ${MUI_PRODUCT} - Data Files in the following folder.$\r$\n$\r$\nTo install in a different folder, click Browse and select another folder. Click Install to start the installation."
EndDirectoryShow: 				
FunctionEnd
 
Function DirectoryLeave
  StrCmp $9 "1" SaveInstallDir
  StrCmp $9 "2" SaveDatabaseDir
  Goto EndDirectoryLeave
 
SaveInstallDir:
  StrCpy $2 $INSTDIR
  Goto EndDirectoryLeave
 
SaveDatabaseDir:
  StrCpy $3 $INSTDIR
 
EndDirectoryLeave:
FunctionEnd
 
Function .onVerifyInstDir
  StrCmp $9 "2" DataPath All
 
DataPath:
;all valid if UNC
  StrCpy $R2 $INSTDIR 2
  StrCmp $R2 "\\" PathOK
 
All:
; Invalid path if root
  Push $INSTDIR
  call GetRoot
  Pop $R1
  StrCmp $R1 $INSTDIR "" PathOK
  Abort
 
PathOK:
FunctionEnd
 
;--------------------------------
;Helper Functions
 
Function GetRoot
  Exch $0
  Push $1
  Push $2
  Push $3
  Push $4
 
  StrCpy $1 $0 2
  StrCmp $1 "\\" UNC
    StrCpy $0 $1
    Goto done
 
UNC:
  StrCpy $2 3
  StrLen $3 $0
  loop:
    IntCmp $2 $3 "" "" loopend
    StrCpy $1 $0 1 $2
    IntOp $2 $2 + 1
    StrCmp $1 "\" loopend loop
  loopend:
    StrCmp $4 "1" +3
      StrCpy $4 1
      Goto loop
    IntOp $2 $2 - 1
    StrCpy $0 $0 $2
 
done:
  Pop $4
  Pop $3
  Pop $2
  Pop $1
  Exch $0
FunctionEnd
