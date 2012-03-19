# define the name of the installer
outfile "gmvault_installer.exe"
 
# define the directory to install to, the desktop in this case as specified  
# by the predefined $DESKTOP variable
installDir $DESKTOP
 
# default section
section

# create a popup box, with an OK button and some text
messageBox MB_OK "Now We are Creating test.txt at Desktop!"
 
# define the output path for this file
setOutPath $INSTDIR
 
# define what to install and place it in the output path
file test.txt
 
sectionEnd
