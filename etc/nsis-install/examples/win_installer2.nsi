# define name of installer
outFile "installer.exe"
 
# define installation directory
installDir $DESKTOP
 
# start default section
section
 
    # set the installation directory as the destination for the following actions
    setOutPath $INSTDIR
 
    # create the uninstaller
    writeUninstaller "$INSTDIR\uninstall.exe"
 
    # create a shortcut named "new shortcut" in the start menu programs directory
    # point the new shortcut at the program uninstaller
    createShortCut "$SMPROGRAMS\new shortcut.lnk" "$INSTDIR\uninstall.exe"
sectionEnd
 
# uninstaller section start
section "uninstall"
 
    # first, delete the uninstaller
    delete "$INSTDIR\uninstall.exe"
 
    # second, remove the link from the start menu
    delete "$SMPROGRAMS\new shortcut.lnk"
 
# uninstaller section end
sectionEnd
