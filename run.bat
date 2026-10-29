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
echo Dang mo Video Maker... (trinh duyet se tu mo; dong cua so nay de tat ung dung)
if not exist "frontend\dist\index.html" (
  echo Chua build giao dien React. Hay chay install.bat truoc.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m videomaker
pause
