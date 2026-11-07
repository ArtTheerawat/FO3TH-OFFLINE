import os
import shutil
import string
import subprocess
import sys

from .config import BASE_DIR, get_game_path, set_game_path

IGNORED_PATH_PATTERNS = [*('$RECYCLE.BIN', 'RECYCLER', 'SYSTEM VOLUME INFORMATION', '\\WINDOWS\\', '\\TEMP\\', '$WINREAGENT', 'RECOVERY')]


def check_game_dir(d):
    if not d or not os.path.isdir(d):
        return False

    d_clean = os.path.abspath(d).upper()
    for bad in IGNORED_PATH_PATTERNS:
        if bad in d_clean:
            return False

    return os.path.isfile(os.path.join(d, 'fifazf.exe'))


def quick_detect_game():
    saved = get_game_path()
    if saved and check_game_dir(saved):
        return saved

    candidates = [
        BASE_DIR,
        os.path.abspath(os.path.join(BASE_DIR, '..')),
        os.path.abspath(os.path.join(BASE_DIR, '..', '..')),
        os.path.abspath(os.path.join(BASE_DIR, 'Game')),
        os.path.abspath(os.path.join(BASE_DIR, '..', 'Game')),
    ]
    for c in candidates:
        if check_game_dir(c):
            set_game_path(c)
            return c

    common = [*('D:\\6.Game\\FO3TH_OFF', 'D:\\6.Game\\FO3TH', 'E:\\FO3TH - Copy', 'E:\\FO3TH', 'D:\\FO3TH', 'C:\\FO3TH', 'D:\\Games\\FO3TH', 'D:\\GarenaFO3\\GameData', 'C:\\GarenaFO3\\GameData', 'C:\\Program Files (x86)\\GarenaFO3\\GameData', 'D:\\Program Files (x86)\\GarenaFO3\\GameData', 'D:\\FO3ID\\32795', 'E:\\FO3ID\\32795', 'C:\\FO3ID\\32795')]
    for c in common:
        if check_game_dir(c):
            set_game_path(c)
            return c

    return None


def deep_scan_game_drives(progress_callback=None):
    drives = [f'{d}:\\' for d in string.ascii_uppercase if os.path.exists(f'{d}:\\')]
    for drv in drives:
        if progress_callback:
            progress_callback(f'[ระบบ] 🔍 กำลังสแกนไดรฟ์ {drv} เพื่อค้นหาเกม FO3...')
        try:
            for root, dirs, files in os.walk(drv):
                dirs[:] = [d for d in dirs if not d.startswith('$') and d.upper() not in ('SYSTEM VOLUME INFORMATION', 'WINDOWS', 'PROGRAMDATA', 'APPDATA', 'TEMP', 'RECOVERY', '$RECYCLE.BIN')]

                if 'fifazf.exe' in files and check_game_dir(root):
                    set_game_path(root)
                    return root

                depth = root.count(os.sep) - drv.count(os.sep)
                if depth >= 3:
                    dirs.clear()
        except Exception:
            continue
    return None


def auto_detect_game():
    found = quick_detect_game()
    if found:
        return found
    return deep_scan_game_drives()


def setup_game_files(game_dir, log_func=print):
    if not check_game_dir(game_dir):
        return False, 'โฟลเดอร์เกมไม่ถูกต้อง (ไม่พบ fifazf.exe)'

    try:
        set_game_path(game_dir)

        src_launcher = os.path.join(BASE_DIR, 'fifalauncher_offline.exe')
        if not os.path.isfile(src_launcher):
            src_launcher = os.path.join(BASE_DIR, 'Client_Patch', 'fifalauncher_offline.exe')

        dst_launcher = os.path.join(game_dir, 'fifalauncher_offline.exe')
        if os.path.isfile(src_launcher) and os.path.abspath(src_launcher) != os.path.abspath(dst_launcher):
            if not os.path.isfile(dst_launcher) or os.path.getsize(dst_launcher) != os.path.getsize(src_launcher):
                shutil.copy2(src_launcher, dst_launcher)
                log_func('[ติดตั้ง] คัดลอก fifalauncher_offline.exe ไปยังโฟลเดอร์เกมแล้ว')

        src_xem = os.path.join(BASE_DIR, 'Xigncode', 'xcorona.xem')
        if not os.path.isfile(src_xem):
            src_xem = os.path.join(BASE_DIR, 'Client_Patch', 'Xigncode', 'xcorona.xem')

        dst_xem_dir = os.path.join(game_dir, 'Xigncode')
        dst_xem = os.path.join(dst_xem_dir, 'xcorona.xem')
        if os.path.isfile(src_xem) and os.path.abspath(src_xem) != os.path.abspath(dst_xem):
            if not os.path.isfile(dst_xem) or os.path.getsize(dst_xem) != os.path.getsize(src_xem):
                os.makedirs(dst_xem_dir, exist_ok=True)
                shutil.copy2(src_xem, dst_xem)
                log_func('[ติดตั้ง] คัดลอก xcorona.xem (Bypass Xigncode) ไปยังโฟลเดอร์เกมแล้ว')

        src_module = os.path.join(BASE_DIR, 'Client_Patch', 'data', 'ui', 'libs', 'Module.big')
        dst_module_dir = os.path.join(game_dir, 'data', 'ui', 'libs')
        dst_module = os.path.join(dst_module_dir, 'Module.big')
        bak_module = os.path.join(dst_module_dir, 'Module.big.bak')
        if os.path.isfile(src_module) and os.path.abspath(src_module) != os.path.abspath(dst_module):
            if not os.path.isfile(dst_module) or os.path.getsize(dst_module) != os.path.getsize(src_module):
                os.makedirs(dst_module_dir, exist_ok=True)
                if os.path.isfile(dst_module) and not os.path.isfile(bak_module):
                    shutil.copy2(dst_module, bak_module)
                shutil.copy2(src_module, dst_module)
                log_func('[ติดตั้ง] คัดลอก Module.big (Patch TTCN) ไปยังโฟลเดอร์เกมแล้ว')

        src_coach_ui = os.path.join(BASE_DIR, 'Client_Patch', 'data', 'ui', 'StartupCoachCreationScreen.big')
        dst_coach_ui_dir = os.path.join(game_dir, 'data', 'ui')
        dst_coach_ui = os.path.join(dst_coach_ui_dir, 'StartupCoachCreationScreen.big')
        bak_coach_ui = os.path.join(dst_coach_ui_dir, 'StartupCoachCreationScreen.big.bak')
        if os.path.isfile(src_coach_ui) and os.path.abspath(src_coach_ui) != os.path.abspath(dst_coach_ui):
            if not os.path.isfile(dst_coach_ui) or os.path.getsize(dst_coach_ui) != os.path.getsize(src_coach_ui):
                os.makedirs(dst_coach_ui_dir, exist_ok=True)
                if os.path.isfile(dst_coach_ui) and not os.path.isfile(bak_coach_ui):
                    shutil.copy2(dst_coach_ui, bak_coach_ui)
                shutil.copy2(src_coach_ui, dst_coach_ui)
                log_func('[ติดตั้ง] คัดลอก StartupCoachCreationScreen.big (Patch 3D ตัวแทน) ไปยังโฟลเดอร์เกมแล้ว')

        return True, 'ติดตั้งไฟล์เกมสำเร็จ'
    except Exception as e:
        log_func(f'[ติดตั้ง] แจ้งเตือนระหว่างคัดลอกไฟล์: {e}')
        return False, str(e)


def launch_game(game_dir, log_func=print):
    if not check_game_dir(game_dir):
        return False, 'ไม่พบ fifazf.exe ในโฟลเดอร์เกม!'

    setup_game_files(game_dir, log_func)

    target_exe = os.path.join(game_dir, 'fifalauncher_offline.exe')
    if not os.path.isfile(target_exe):
        target_exe = os.path.join(BASE_DIR, 'fifalauncher_offline.exe')

    if not os.path.isfile(target_exe):
        return False, 'ไม่พบไฟล์ fifalauncher_offline.exe!'

    try:
        env = os.environ.copy()
        env['__COMPAT_LAYER'] = 'RunAsInvoker'
        log_func(f'[เกม] กำลังเปิดเกมจาก: {target_exe}')
        subprocess.Popen([target_exe], cwd=game_dir, env=env)
        return True, 'เปิดเกมสำเร็จ!'
    except Exception as e:
        return False, f'เปิดเกมผิดพลาด: {e}'
