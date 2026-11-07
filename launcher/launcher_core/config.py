import json
import os
import sys


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
GAME_PATH_FILE = os.path.join(BASE_DIR, 'game_path.txt')

DEFAULT_CONFIG = {
    'app_name': 'FO3TH OFFLINE',
    'version': '1.0.0',
    'author': 'FO3TH OFFLINE (ต้นฉบับ: Ý Trịnh)',
    'zalo_link': 'https://zalo.me/0905020696',
    'zalo_phone': '0905.020.696',
    'fb_group_link': 'https://www.facebook.com/groups/congdongfo3vietnam',
    'bank_name': 'Vietcombank',
    'bank_account_name': 'TRINH NHU Y',
    'bank_account_number': '0431000215103',
    'logo_image_file': 'images/logo_fo3.png',
    'qr_image_file': 'images/donate_qr.jpg',
    'github_repo': 'ArtTheerawat/FO3TH-OFFLINE',
    'admin_url': 'http://127.0.0.1:8088/',
    'python_path': '',
}


def load_config():
    """
โหลดค่าตั้งค่าของแอปพลิเคชัน:
- เมื่อแพ็กเป็น EXE (บนเครื่องผู้เล่น): ใช้ค่าตั้งค่าที่ฝังไว้ในโค้ดโดยตรง
  เพื่อป้องกันการแก้ไขเลขบัญชีสนับสนุน ผู้พัฒนา หรือการปลอมเวอร์ชันอย่างสิ้นเชิง
- เมื่อรันในสภาพแวดล้อมพัฒนา (Dev): อ่านจาก config.json ถ้ามีไฟล์อยู่
"""
    config = DEFAULT_CONFIG.copy()
    if getattr(sys, 'frozen', False):

        return config


    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            config.update(loaded)
        except Exception as e:
            print(f'[Config] อ่าน config.json ผิดพลาด: {e}')
    return config


def save_config(config):
    'บันทึกค่าตั้งค่าลง config.json (ใช้เฉพาะสภาพแวดล้อม Dev เท่านั้น ไม่สร้างไฟล์บนเครื่องผู้เล่น)'
    if getattr(sys, 'frozen', False):
        return None
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f'[Config] บันทึก config.json ผิดพลาด: {e}')
    return None

IGNORED_PATH_PATTERNS = ['$RECYCLE.BIN', 'RECYCLER', 'SYSTEM VOLUME INFORMATION', '\\WINDOWS\\', '\\TEMP\\', '$WINREAGENT', 'RECOVERY']


















def get_game_path():
    if os.path.exists(GAME_PATH_FILE):
        try:
            with open(GAME_PATH_FILE, 'r', encoding='utf-8') as f:
                path = f.read().strip()
            if path:
                p_upper = os.path.abspath(path).upper()
                if any(bad in p_upper for bad in IGNORED_PATH_PATTERNS):
                    return ''
                if os.path.exists(os.path.join(path, 'fifazf.exe')):
                    return path
        except Exception:
            pass
    return ''


def set_game_path(path):
    try:
        with open(GAME_PATH_FILE, 'w', encoding='utf-8') as f:
            f.write(path)
        return True
    except Exception as e:
        print(f'[Config] เขียน game_path.txt ผิดพลาด: {e}')
        return False
