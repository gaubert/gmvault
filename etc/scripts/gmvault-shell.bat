@rem Do not use "echo off" to not affect any child calls.
@setlocal
@TITLE GMVAULT-SHELL
@REM change prompt
@prompt gmvault-shell$G

@rem Get the absolute path to the current directory, which is assumed to be the
@rem Gmvault installation root and add the gmv_app dir in the path
@for /F "delims=" %%I in ("%~dp0") do @set gmvault_install_root=%%~fI
@set PATH=%gmvault_install_root%;%gmvault_install_root%\gmv_app;%PATH%

@if not exist "%HOME%" @set HOME=%HOMEDRIVE%%HOMEPATH%
@if not exist "%HOME%" @set HOME=%USERPROFILE%

@cd %HOME%
@start "GMVAULT-SHELL" gmv-msg.bat  
