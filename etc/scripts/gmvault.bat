@ECHO OFF

REM SET HOME to HOMEPATH because with py2exe it doesn't work
SET HOME=%HOMEDRIVE%%HOMEPATH%

:: Push in this script directory to run
pushd %~dp0%
gmv_runner.exe %*
set err=%errorlevel%
popd
::return error code from gmv_cmd
exit /b %err%
