@echo off
rem ============================================================
rem  สคริปต์ Build FO3TH OFFLINE Launcher
rem  ใช้: ดับเบิลคลิกไฟล์นี้ (หรือรันจาก cmd) เมื่อแก้โค้ดเสร็จ
rem  ผลลัพธ์: dist\FO3TH_Launcher.exe
rem
rem  ข้อกำหนด (ติดตั้งครั้งแรกครั้งเดียว):
rem    1. Python 3.15  อยู่ที่ %LOCALAPPDATA%\Programs\Python\Python315
rem    2. รันคำสั่งนี้ครั้งแรก:
rem       "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python315\python.exe" -m pip install customtkinter pillow requests pyinstaller
rem ============================================================

setlocal
set PY=%LOCALAPPDATA%\Programs\Python\Python315\python.exe
if not exist "%PY%" (
    echo [ผิดพลาด] ไม่พบ Python 3.15 ที่: %PY%
    echo ติดตั้ง Python 3.15 จาก https://www.python.org/downloads/ ก่อน
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [1/3] ตรวจสอบ syntax ทุกไฟล์...
"%PY%" -c "import py_compile, glob; [py_compile.compile(f, doraise=True) for f in glob.glob('launcher/**/*.py', recursive=True)]"
if errorlevel 1 (
    echo [ผิดพลาด] โค้ดมี syntax error — แก้ก่อนแล้วลองใหม่
    pause
    exit /b 1
)

echo [2/3] Build EXE ด้วย PyInstaller (ใช้เวลา 1-3 นาที)...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name FO3TH_Launcher ^
    --icon assets\app_icon.ico ^
    --add-data "assets;assets" ^
    --hidden-import customtkinter ^
    --collect-all customtkinter ^
    launcher\FO3_Launcher.py
if errorlevel 1 (
    echo [ผิดพลาด] Build ล้มเหลว
    pause
    exit /b 1
)

echo [3/3] เสร็จแล้ว!
echo ไฟล์ EXE อยู่ที่: %~dp0dist\FO3TH_Launcher.exe
echo.
echo ขั้นตอนอัพเดตให้ผู้เล่น (ดูรายละเอียดใน docs\วิธีอัพเดต.md):
echo   1. เปลี่ยน 'version' ใน launcher\launcher_core\config.py ให้สูงขึ้น
echo   2. build ใหม่ด้วยสคริปต์นี้
echo   3. อัพโหลด EXE ไปที่ GitHub Releases ของ ArtTheerawat/FO3TH-OFFLINE
echo.
pause
