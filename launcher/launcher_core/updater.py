import json
import os
import re
import shutil
import subprocess
import sys
import threading
import zipfile
import requests

from .backup_manager import backup_save
from .config import BASE_DIR, load_config

TEMP_DIR = os.path.join(BASE_DIR, 'temp_update')


def parse_version(v_str):
    "แยก tuple ตัวเลขออกมา (เช่น: 'v1.0.1' -> (1, 0, 1)) เพื่อใช้เปรียบเทียบ"
    if not v_str:
        return (0, 0, 0)
    cleaned = re.sub('[^0-9.]', '', v_str)
    parts = cleaned.split('.')
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    while len(result) < 3:
        result.append(0)
    return tuple(result)


def check_for_updates(github_repo=None):
    """
ตรวจสอบเวอร์ชันใหม่จาก GitHub Releases
คืนค่า: (has_update, new_version, changelog, download_url, asset_name)
"""
    config = load_config()
    current_ver = config.get('version', '1.0.0')
    repo = github_repo or config.get('github_repo', '')

    if not repo or '/' not in repo:
        return (False, current_ver, 'ยังไม่ได้ตั้งค่า GitHub Repo (รูปแบบ: Username/Repository)', None, None)

    url = f'https://api.github.com/repos/{repo}/releases/latest'
    try:
        headers = {'User-Agent': 'FO3-Offline-Launcher'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 404:
            return (False, current_ver, f"ไม่พบ Release ใด ๆ บน GitHub repo '{repo}'.", None, None)
        if resp.status_code != 200:
            return (False, current_ver, f'เซิร์ฟเวอร์ GitHub ผิดพลาด (รหัส {resp.status_code})', None, None)

        data = resp.json()
        latest_tag = data.get('tag_name', '')
        changelog = data.get('body', 'ไม่มีข้อมูลรายละเอียด')
        assets = data.get('assets', [])


        download_url = None
        asset_name = None


        for asset in assets:
            name = asset.get('name', '').lower()
            if name.endswith('.zip') and ('setup' in name or 'installer' in name or 'fo3' in name):
                download_url = asset.get('browser_download_url')
                asset_name = asset.get('name')
                break


        if not download_url:
            for asset in assets:
                name = asset.get('name', '').lower()
                if not name.endswith('.exe'): continue
                download_url = asset.get('browser_download_url')
                asset_name = asset.get('name')
                break

        if not download_url:
            for asset in assets:
                name = asset.get('name', '').lower()
                if not name.endswith('.zip'): continue
                download_url = asset.get('browser_download_url')
                asset_name = asset.get('name')
                break

        if not download_url:
            download_url = data.get('zipball_url')
            asset_name = f'{latest_tag}.zip'

        latest_ver_tuple = parse_version(latest_tag)
        current_ver_tuple = parse_version(current_ver)

        if latest_ver_tuple > current_ver_tuple:
            return (True, latest_tag, changelog, download_url, asset_name)

        return (False, current_ver, 'คุณใช้เวอร์ชันล่าสุดอยู่แล้ว!', None, None)

    except requests.RequestException as e:
        return (False, current_ver, f'การเชื่อมต่อเครือข่ายผิดพลาด: {e}', None, None)
    except Exception as e:
        return (False, current_ver, f'ตรวจสอบอัพเดตผิดพลาด: {e}', None, None)


def download_file(url, target_path, progress_callback=None, cancel_event=None):
    """
ดาวน์โหลดไฟล์จาก URL และรายงานความคืบหน้า % ผ่าน progress_callback
"""
    headers = {'User-Agent': 'FO3-Offline-Launcher'}
    with requests.get(url, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        total_length = int(r.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 65536

        with open(target_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if cancel_event and cancel_event.is_set():
                    return False
                if not chunk: continue
                f.write(chunk)
                downloaded += len(chunk)
                if total_length > 0 and progress_callback:
                    percent = int(downloaded / total_length * 100)
                    progress_callback(percent, downloaded, total_length)
    return True


def apply_setup_update(setup_exe_path, log_func=print):
    """
รันไฟล์ติดตั้ง Inno Setup ในโหมดเงียบสนิท (/VERYSILENT)
สำรองข้อมูลอัตโนมัติ เก็บโฟลเดอร์ gamedata ไว้ ปิด Launcher ปัจจุบัน
ติดตั้งทับไฟล์ใหม่ กู้คืนข้อมูล gamedata และเปิด FO3_Launcher.exe ขึ้นมาใหม่อัตโนมัติ
"""
    log_func('[อัพเดต] กำลังสำรองข้อมูลเซฟก่อนอัพเกรด...')
    backup_save(log_func)


    preserve_dir = os.path.join(BASE_DIR, 'temp_gamedata_save')
    gamedata_dir = os.path.join(BASE_DIR, 'Server', 'gamedata')
    try:
        if os.path.exists(gamedata_dir):
            if os.path.exists(preserve_dir):
                shutil.rmtree(preserve_dir, ignore_errors=True)
            shutil.copytree(gamedata_dir, preserve_dir)
            log_func('[อัพเดต] เก็บข้อมูลผู้จัดการทีมและเซฟไว้อย่างปลอดภัยก่อนติดตั้งทับแล้ว')
    except Exception as e:
        log_func(f'[อัพเดต] หมายเหตุการเก็บรักษาข้อมูล: {e}')

    updater_bat = os.path.join(BASE_DIR, 'silent_updater.bat')
    launcher_exe = os.path.join(BASE_DIR, 'FO3_Launcher.exe')

    log_func('[อัพเดต] กำลังเตรียมปิด Launcher เพื่อติดตั้งทับเวอร์ชันใหม่...')

    bat_content = f'''@echo off
chcp 65001 >nul

rem ล้างตัวแปรสภาพแวดล้อม PyInstaller และ Python ทั้งหมด เพื่อไม่ให้สืบทอดโฟลเดอร์ temp เดิม
for /f "tokens=1 delims==" %%v in ('set _PYI_ 2^>nul') do set %%v=
for /f "tokens=1 delims==" %%v in ('set _MEI 2^>nul') do set %%v=
set _MEIPASS2=
set _MEIPASS=
set _PYI_APPLICATION_HOME_DIR=
set _PYI_ARCHIVE_FILE=
set _PYI_PARENT_PROCESS_LEVEL=
set _PYI_SPLASH_IPC=
set PYTHONPATH=
set PYTHONHOME=

rem 1. รอ 2 วินาทีเพื่อให้โปรเซส Launcher ปัจจุบันปิดสนิท
timeout /t 2 /nobreak >nul
rem 2. บังคับปิด FO3_Launcher ทุกอินสแตนซ์ที่ยังเหลืออยู่
taskkill /F /IM FO3_Launcher.exe >nul 2>&1
timeout /t 1 /nobreak >nul
rem 3. รันโปรแกรมติดตั้งลงโฟลเดอร์ปัจจุบัน
start /wait "" "{setup_exe_path}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="{BASE_DIR}"

rem 3.1. ปกป้องอย่างเด็ดขาด: กู้คืนข้อมูลผู้จัดการทีมและเซฟเกมจากไฟล์ snapshot กันโปรแกรมติดตั้งเขียนทับ
if exist "{preserve_dir}" (
    xcopy /E /Y /I "{preserve_dir}" "{gamedata_dir}" >nul 2>&1
    rd /s /q "{preserve_dir}" >nul 2>&1
)

rem 4. รอโปรแกรมติดตั้งเสร็จสิ้นแล้วเริ่ม Launcher ใหม่อีกครั้ง
timeout /t 2 /nobreak >nul

rem ล้างตัวแปรสภาพแวดล้อม PyInstaller ซ้ำก่อนเริ่มทำงาน
for /f "tokens=1 delims==" %%v in ('set _PYI_ 2^>nul') do set %%v=
for /f "tokens=1 delims==" %%v in ('set _MEI 2^>nul') do set %%v=
set _MEIPASS2=
set _MEIPASS=
set _PYI_APPLICATION_HOME_DIR=
set _PYI_ARCHIVE_FILE=
set _PYI_PARENT_PROCESS_LEVEL=
set _PYI_SPLASH_IPC=
set PYTHONPATH=
set PYTHONHOME=

start "" /D "{BASE_DIR}" "{launcher_exe}"

rem 5. ลบไฟล์ติดตั้งชั่วคราวและโฟลเดอร์ temp_update ถ้ามี
del /F /Q "{setup_exe_path}" >nul 2>&1
if exist "{BASE_DIR}\\temp_update" rd /s /q "{BASE_DIR}\\temp_update" >nul 2>&1
(goto) 2>nul & del /F /Q "%~f0" & exit
'''
    try:
        with open(updater_bat, 'w', encoding='utf-8') as f:
            f.write(bat_content)

        clean_env = os.environ.copy()
        keys_to_del = [k for k in clean_env if k.startswith(('_PYI_', '_MEI', 'PYTHON'))]
        for k in keys_to_del:
            clean_env.pop(k, None)


        DETACHED_PROCESS = 8
        CREATE_NEW_PROCESS_GROUP = 512
        flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0

        subprocess.Popen(
            ['cmd.exe', '/c', updater_bat],
            cwd=BASE_DIR,
            env=clean_env,
            creationflags=flags,
            close_fds=True,
        )
        return True
    except Exception as e:
        log_func(f'[อัพเดต] เริ่มการติดตั้งทับผิดพลาด: {e}')
        return False


def apply_zip_update(zip_path, log_func=print):
    """
แตกไฟล์อัพเดตทับลงโฟลเดอร์แอปพลิเคชัน โดยห้ามเขียนทับไฟล์เหล่านี้เด็ดขาด:
- Server/gamedata/ (ถ้าไฟล์มีอยู่แล้ว)
- game_path.txt
- config.json
"""
    log_func('[อัพเดต] กำลังสำรองข้อมูลเซฟก่อนอัพเดต...')
    backup_save(log_func)

    log_func('[อัพเดต] กำลังแตกไฟล์อัพเดต...')
    has_new_launcher = False
    new_launcher_path = os.path.join(BASE_DIR, 'FO3_Launcher_new.exe')

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            filename = file_info.filename.replace('\\', '/')

            parts = filename.split('/')
            if len(parts) > 1 and parts[0].startswith(parts[0]):
                if len(parts) >= 2 and ('Server' in parts[1] or 'Client_Patch' in parts[1] or 'Xigncode' in parts[1]):
                    rel_path = '/'.join(parts[1:])
                else:
                    rel_path = filename
            else:
                rel_path = filename

            if not rel_path or rel_path.endswith('/'):
                continue

            target_file = os.path.join(BASE_DIR, rel_path.replace('/', os.sep))
            os.makedirs(os.path.dirname(target_file), exist_ok=True)


            if 'gamedata' in rel_path.lower():
                if os.path.exists(target_file):
                    log_func(f'[อัพเดต] คงข้อมูลส่วนตัวไว้เดิม: {rel_path}')
                    continue
            elif 'game_path.txt' in rel_path.lower() or 'config.json' in rel_path.lower():
                if os.path.exists(target_file):
                    log_func(f'[อัพเดต] คงค่าตั้งค่าส่วนตัวไว้เดิม: {rel_path}')
                    continue

            if os.path.basename(target_file).lower() == 'fo3_launcher.exe':
                has_new_launcher = True
                with zip_ref.open(file_info) as source, open(new_launcher_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                continue

            try:
                with zip_ref.open(file_info) as source, open(target_file, 'wb') as target:
                    shutil.copyfileobj(source, target)
            except Exception as e:
                log_func(f'[อัพเดต] ข้ามไฟล์ที่ถูกใช้งานอยู่ ({rel_path}): {e}')

    log_func('[อัพเดต] อัพเดตไฟล์ข้อมูลสำเร็จแล้ว!')

    if has_new_launcher and os.path.exists(new_launcher_path):
        log_func('[อัพเดต] พบเวอร์ชัน Launcher ใหม่ กำลังเตรียมสลับไฟล์...')
        create_and_run_swap_script()

    return True


def create_and_run_swap_script():
    'สร้างไฟล์ updater.bat ชั่วคราวเพื่อสลับ FO3_Launcher.exe'
    updater_bat = os.path.join(BASE_DIR, 'updater.bat')
    current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.join(BASE_DIR, 'FO3_Launcher.exe')
    new_exe = os.path.join(BASE_DIR, 'FO3_Launcher_new.exe')

    bat_content = f'''@echo off
rem ล้างตัวแปรสภาพแวดล้อมที่เกี่ยวข้องกับ PyInstaller และ Python ทั้งหมด
for /f "tokens=1 delims==" %%v in ('set _PYI_ 2^>nul') do set %%v=
for /f "tokens=1 delims==" %%v in ('set _MEI 2^>nul') do set %%v=
set _MEIPASS2=
set _MEIPASS=
set _PYI_APPLICATION_HOME_DIR=
set _PYI_ARCHIVE_FILE=
set _PYI_PARENT_PROCESS_LEVEL=
set _PYI_SPLASH_IPC=
set PYTHONPATH=
set PYTHONHOME=

timeout /t 2 /nobreak >nul
:RETRY
del "{current_exe}" 2>nul
if exist "{current_exe}" (
    timeout /t 1 /nobreak >nul
    goto RETRY
)
move /y "{new_exe}" "{current_exe}"

for /f "tokens=1 delims==" %%v in ('set _PYI_ 2^>nul') do set %%v=
for /f "tokens=1 delims==" %%v in ('set _MEI 2^>nul') do set %%v=
set _MEIPASS2=
set _MEIPASS=
set _PYI_APPLICATION_HOME_DIR=
set _PYI_ARCHIVE_FILE=
set _PYI_PARENT_PROCESS_LEVEL=
set _PYI_SPLASH_IPC=
set PYTHONPATH=
set PYTHONHOME=

start "" /D "{BASE_DIR}" "{current_exe}"
del "%~f0" & exit
'''
    try:
        with open(updater_bat, 'w', encoding='utf-8') as f:
            f.write(bat_content)

        clean_env = os.environ.copy()
        keys_to_del = [k for k in clean_env if k.startswith(('_PYI_', '_MEI', 'PYTHON'))]
        for k in keys_to_del:
            clean_env.pop(k, None)

        subprocess.Popen(
            ['cmd.exe', '/c', updater_bat],
            cwd=BASE_DIR,
            env=clean_env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        sys.exit(0)
    except Exception as e:
        print(f'[Updater] สลับ launcher ผิดพลาด: {e}')
