import ctypes
import os
import stat
import subprocess
import sys


HOSTS_PATH = 'C:\\Windows\\System32\\drivers\\etc\\hosts'
ENTRY_IP = '127.0.0.1'
ENTRY_HOST = 'APSEODESK172'
ENTRY_LINE = f'{ENTRY_IP} {ENTRY_HOST}'


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def remove_readonly(path):
    'ลบแอตทริบิวต์ Read-only, System, Hidden ถ้ามี'
    if not os.path.exists(path):
        return None
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except Exception:
        pass
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path, 128)
    except Exception:
        pass
    try:
        subprocess.run(
            ['attrib', '-r', '-s', '-h', path],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
    except Exception:
        return None
    return None
































def is_hosts_configured():
    if not os.path.exists(HOSTS_PATH):
        return False
    try:
        with open(HOSTS_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_clean = line.strip().upper()
                if ENTRY_HOST.upper() not in line_clean:
                    continue
                if line_clean.startswith('#'):
                    continue
                return True
    except Exception as e:
        print(f'[Hosts] อ่าน hosts ผิดพลาด: {e}')
    return False


def open_hosts_in_notepad():
    'เปิดไฟล์ hosts ใน Notepad ด้วยสิทธิ์ Administrator'
    try:
        subprocess.run(
            [
                'powershell', '-NoProfile', '-Command',
                f"Start-Process notepad.exe -ArgumentList '{HOSTS_PATH}' -Verb RunAs",
            ],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        return True
    except Exception:
        return False


def install_hosts():
    """
ตรวจสอบและเพิ่ม entry ลงไฟล์ hosts
รองรับการลบแอตทริบิวต์ Read-Only อัตโนมัติ พร้อม fallback ผ่าน PowerShell RunAs และ CMD RunAs
    """
    if is_hosts_configured():
        return (True, 'Hosts ถูกติดตั้งไว้ก่อนหน้านี้แล้ว')

    remove_readonly(HOSTS_PATH)
    try:
        with open(HOSTS_PATH, 'a', encoding='utf-8') as f:
            f.write(f'\n{ENTRY_LINE}\n')
    except Exception:
        pass
    if is_hosts_configured():
        return (True, 'ติดตั้ง Hosts สำเร็จ!')

    try:
        ps_cmd = (
            f"attrib -r -s -h '{HOSTS_PATH}'"
            f"'; Add-Content -Path '{HOSTS_PATH}'"
            f"' -Value '`n{ENTRY_LINE}' -Force"
        )
        subprocess.run(
            [
                'powershell', '-NoProfile', '-Command',
                f"Start-Process powershell -ArgumentList '-NoProfile -Command \"{ps_cmd}\"' -Verb RunAs -Wait",
            ],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
    except Exception:
        pass
    if is_hosts_configured():
        return (True, 'ติดตั้ง Hosts สำเร็จ (ได้รับสิทธิ์ Administrator แล้ว)!')

    try:
        cmd_arg = (
            f'attrib -r "{HOSTS_PATH}" & echo. >> "{HOSTS_PATH}"'
            f' & echo {ENTRY_LINE} >> "{HOSTS_PATH}"'
        )
        subprocess.run(
            [
                'powershell', '-NoProfile', '-Command',
                f"Start-Process cmd.exe -ArgumentList '/c \"{cmd_arg}\"' -Verb RunAs -Wait",
            ],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
    except Exception:
        pass
    if is_hosts_configured():
        return (True, 'ติดตั้ง Hosts สำเร็จ!')

    if is_hosts_configured():
        return (True, 'ติดตั้ง Hosts สำเร็จ!')

    return (False, f"เขียนลงไฟล์ Hosts ไม่สำเร็จ: '{HOSTS_PATH}'.\n\nสาเหตุที่เป็นไปได้:\n1. ไฟล์ Hosts ถูกล็อกแอตทริบิวต์ Read-only (อ่านอย่างเดียว) อยู่\n2. ซอฟต์แวร์ป้องกันไวรัส (Windows Defender, Avast, Kaspersky ฯลฯ) กำลังล็อกป้องกันไฟล์ Hosts อยู่\n3. คุณได้ปฏิเสธคำขอสิทธิ์ UAC (Run as Administrator)")
