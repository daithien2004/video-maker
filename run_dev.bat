@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
set "TEMP=%~dp0work\browser_temp"
set "TMP=%TEMP%"
set "TMPDIR=%TEMP%"
if not exist "%TEMP%" mkdir "%TEMP%"
if not exist ".venv\Scripts\python.exe" (
  echo Chua cai dat. Hay chay install.bat truoc.
  pause
  exit /b 1
)
echo Che do phat trien: sua code trong videomaker hoac frontend, app tu build va khoi dong lai.
echo Dong cua so nay de tat ung dung.
".venv\Scripts\python.exe" tools\dev.py
pause
