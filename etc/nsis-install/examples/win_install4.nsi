; example1.nsi
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
InstallDir $PROGRAMFILES\gmvault

; The text to prompt the user to enter a directory
DirText "Please Choose a directory where to install gmvault"

;--------------------------------

; The stuff to install
Section "" ;No components page, name is not important

; Set output path to the installation directory.
SetOutPath $INSTDIR

; Put file there
File test.txt

SectionEnd ; end the section
