@echo off
setlocal enabledelayedexpansion

cls
echo   ###                ###
echo  # Beembot           #
echo ###                ###
echo.

set "botFile=WatchDog.py"
set "pyPath=python"

for /f "tokens=*" %%i in ('where python 2^>nul') do (
    set "p=%%i"
    if /i NOT "!p:~0,5!"=="INFO:" (
        set "pyPath=%%i"
    )
)

set "thisDir=%~dp0"

goto start

:update
pushd "%thisDir%"
echo Updating...
echo.
git pull
echo.
popd
goto :EOF

:start
if /i "%update%" == "Yes" (
    call :update
)

"%pyPath%" "%botFile%"

pause > nul