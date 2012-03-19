@ECHO OFF

::SET HOME to HOMEPATH because with py2exe it doesn't work
SET HOME=%HOMEPATH%:

EXE_DIR=H:\Dev\projects\gmvault\dist\inst
::SET PATH=H:\Dev\projects\gmvault\dist\inst;%PATH%
pushd %EXE_DIR%
gmv_cmd.exe
popd