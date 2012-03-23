@ECHO OFF

REM SET HOME to HOMEPATH because with py2exe it doesn't work
SET HOME=%HOMEDRIVE%%HOMEPATH%

REM EXE_DIR=H:\Dev\projects\gmvault\dist\inst
SET EXE_DIR=@PATHTOREPLACE@
pushd %EXE_DIR%
gmv_cmd.exe %*
popd
