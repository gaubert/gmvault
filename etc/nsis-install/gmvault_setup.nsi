; gmvault.nsi
;
; This script is perhaps one of the simplest NSIs you can make. All of the
; optional settings are left to their default settings. The installer simply 
; prompts the user asking them where to install, and drops a copy of "MyProg.exe"
; there.

;--------------------------------

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

; The stuff to install
Section "" ;No components page, name is not important

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
