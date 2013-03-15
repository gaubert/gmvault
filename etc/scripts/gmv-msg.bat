@ECHO OFF
@color 2
REM add large console with big buffer screen (if lines < 70 then lines defines the size of the window)
@mode con:cols=140 lines=250

REM To print a message in console once the gmvault-shell has been launched
ECHO Welcome to gmvault (version ###GMVAULTVERSION###). 
ECHO.
ECHO Run gmvault --help to display the help.
ECHO Run gmvault {command} --help to display help for specific commands.
