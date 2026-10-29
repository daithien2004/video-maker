@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
echo ==============================================
echo   CAI DAT VIDEO MAKER (chi can chay 1 lan)
echo ==============================================

rem ---- 1. Tim Python (3.10 - 3.13) ----
set "PY="
for %%V in (3.11 3.12 3.13 3.10) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys; assert (3,10)<=sys.version_info[:2]<=(3,13)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo.
  echo [LOI] Khong tim thay Python 3.10 - 3.13.
  echo       Cai Python 3.11 tai: https://www.python.org/downloads/windows/
  echo       Khi cai nho tick o "Add python.exe to PATH", sau do chay lai file nay.
  pause
  exit /b 1
)
echo [OK] Dung Python: %PY%

rem ---- 2. Tao moi truong ao + cai thu vien ----
if not exist ".venv\Scripts\python.exe" (
  echo Dang tao moi truong ao...
  %PY% -m venv .venv
  if errorlevel 1 ( echo [LOI] Khong tao duoc moi truong ao. & pause & exit /b 1 )
)
echo Dang cai thu vien (co the mat vai phut)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 ( echo [LOI] Cai thu vien that bai. Kiem tra Internet roi chay lai. & pause & exit /b 1 )

echo Dang cai Chromium cho chuc nang Threads...
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 ( echo [LOI] Khong cai duoc Chromium. Chay lai install.bat khi co mang. & pause & exit /b 1 )

rem ---- 3. FFmpeg ----
set "HAVE_FF="
if exist "ffmpeg" (
  for /r "ffmpeg" %%F in (ffmpeg.exe) do if exist "%%F" set "HAVE_FF=1"
)
if not defined HAVE_FF (
  echo Dang tai FFmpeg, khoang 150 MB. Vui long cho...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg_download.zip'; if (Test-Path 'ffmpeg_tmp') { Remove-Item -Recurse -Force 'ffmpeg_tmp' }; Expand-Archive -Force 'ffmpeg_download.zip' -DestinationPath 'ffmpeg_tmp'"
  if errorlevel 1 (
    echo [LOI] Khong tai duoc FFmpeg. Xem muc "FFmpeg thu cong" trong docs\HUONG_DAN.txt
    pause
    exit /b 1
  )
  if exist "ffmpeg" rmdir /s /q "ffmpeg"
  mkdir "ffmpeg"
  for /d %%D in (ffmpeg_tmp\*) do xcopy /e /i /q /y "%%D" "ffmpeg" >nul
  rmdir /s /q "ffmpeg_tmp"
  del /q "ffmpeg_download.zip"
)
echo [OK] FFmpeg san sang.

rem ---- 4. Build giao dien React ----
where node >nul 2>&1
if errorlevel 1 (
  echo [LOI] Can Node.js 22.12+ de build giao dien React. Cai Node.js roi chay lai install.bat.
  pause
  exit /b 1
)
echo Dang cai thu vien va build giao dien React...
pushd frontend
call npm.cmd ci
if errorlevel 1 (
  popd
  echo [LOI] Khong cai duoc thu vien giao dien.
  pause
  exit /b 1
)
call npm.cmd run build
if errorlevel 1 (
  popd
  echo [LOI] Build giao dien that bai.
  pause
  exit /b 1
)
popd

echo.
echo ==============================================
echo   XONG! Bam dup run.bat de mo ung dung.
echo ==============================================
pause
