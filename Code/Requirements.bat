@echo off
setlocal EnableDelayedExpansion
title MotionCode Installer

set "REPO=https://github.com/WinterRupert/MotionCode.git"
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

cls
echo.
echo  ############################################################
echo  #                                                          #
echo  #    _    ____  _____   _   _  ___  _   _   _              #
echo  #   / \  |  _ \| ____| | \ | |/ _ \| | | | | |             #
echo  #  / _ \ | |_) |  _|   |  \| | | | | | | | | |             #
echo  # / ___ \|  _ <| |___  | |\  | |_| | |_| | |_|             #
echo  #/_/   \_\_| \_\_____| |_| \_|\___/ \___/  (_)             #
echo  #                                                          #
echo  #            ARE YOU SURE YOU WANT TO INSTALL?             #
echo  #                                                          #
echo  ############################################################
echo.
echo  This will download MotionCode from GitHub and install
echo  its Python packages into:
echo     !HERE!\MotionCode
echo.
choice /c YN /m "  Type Y to install, N to cancel"
if errorlevel 2 (
    echo Installation cancelled.
    pause
    exit /b 0
)

set "INSTALL_DIR=!HERE!\MotionCode"

echo.
echo === Checking for Git and Python ===
where git >nul 2>&1
if errorlevel 1 (
    echo Git is not installed. Install it from https://git-scm.com and run this again.
    pause
    exit /b 1
)
where py >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Install it from https://www.python.org and run this again.
    pause
    exit /b 1
)

echo.
echo === Downloading MotionCode from GitHub ===
if exist "!INSTALL_DIR!\.git" (
    git -C "!INSTALL_DIR!" pull
) else (
    git clone "%REPO%" "!INSTALL_DIR!"
)
if errorlevel 1 (
    echo Download failed. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo === Finding requirements.txt ===
set "REQ="
if exist "!INSTALL_DIR!\Data\requirements.txt" set "REQ=!INSTALL_DIR!\Data\requirements.txt"
if not defined REQ if exist "!INSTALL_DIR!\requirements.txt" set "REQ=!INSTALL_DIR!\requirements.txt"
if not defined REQ (
    echo Could not find requirements.txt in Data\ or the repo root.
    pause
    exit /b 1
)
echo Found: !REQ!

echo.
echo === Installing Python packages ===
py -3 -m pip install --upgrade pip
py -3 -m pip install -r "!REQ!"
if errorlevel 1 (
    echo Package install failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo === Creating a Start menu shortcut ===
set "RUNNER=!INSTALL_DIR!\Code\main.py"
set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\MotionCode.lnk"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');$s.TargetPath='py';$s.Arguments='-3 \"!RUNNER!\"';$s.WorkingDirectory='!INSTALL_DIR!\Code';$s.Save()"

echo.
echo ############################################################
echo  Done. MotionCode is installed in:
echo  !INSTALL_DIR!
echo  Open MotionCode from your Start menu.
echo ############################################################
pause
endlocal