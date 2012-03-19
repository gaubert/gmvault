; gmvault.nsi
;
; This script is perhaps one of the simplest NSIs you can make. All of the
; optional settings are left to their default settings. The installer simply 
; prompts the user asking them where to install, and drops a copy of "MyProg.exe"
; there.

;--------------------------------
!include "MUI.nsh"

; The name of the installer
Name "gmvault_setup"

; The file to write
OutFile "gmvault_setup.exe"

; The default installation directory
;InstallDir $PROGRAMFILES\gmvault
InstallDir d:\Programs\gmvault

; The text to prompt the user to enter a directory
DirText "Please Choose a directory where to install gmvault"

;--------------------------------
; MUI Settings / Icons
!define MUI_ICON "new_gmvault.ico"
;!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\orange-uninstall-nsis.ico"

; MUI Settings / Header
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP ".\Orange-Full-MoNKi\Header\orange-r-nsis.bmp"
!define MUI_HEADERIMAGE_UNBITMAP ".\Orange-Full-MoNKi\Header\orange-r-nsis.bmp"

; MUI Settings / Wizard
!define MUI_WELCOMEFINISHPAGE_BITMAP "gmvault.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP ".\Orange-Full-MoNKi\Wizard\orange-uninstall-nsis.bmp"


!define MUI_WELCOMEPAGE_TITLE "GMVAULT Setup"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "License.rtf"
!insertmacro MUI_PAGE_DIRECTORY 
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

LangString msg ${LANG_ENGLISH} "English msg"

; The stuff to install
Section "gmvault" ;No components page, name is not important


; Set output path to the installation directory.
SetOutPath $INSTDIR

; Put file there
File gmv_cmd.exe
File library.zip
File python27.dll
File w9xpopen.exe
File *.pyd
File /r Microsoft.VC90.CRT

; =================================================
; Uninstaller
; =================================================
WriteUninstaller $INSTDIR\Uninstall.exe

SectionEnd ; end the section

; The uninstall section
Section "Uninstall"

Delete $INSTDIR\Uninstall.exe
Delete $INSTDIR\MyProg.exe
Delete $INSTDIR\gmv_cmd.exe
Delete $INSTDIR\library.zip
Delete $INSTDIR\python27.dll
Delete $INSTDIR\w9xpopen.exe
Delete $INSTDIR\*.pyd
RMDir /r Microsoft.VC90.CRT
RMDir $INSTDIR


SectionEnd ; end the section
