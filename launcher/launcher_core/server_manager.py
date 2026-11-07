import glob
import os
import shutil
import subprocess
import sys
import threading
import time

from .config import BASE_DIR, load_config

SERVER_DIR = os.path.join(BASE_DIR, 'Server')


def get_clean_py_env(extra_env=None):
    env = os.environ.copy()
    keys_to_del = [k for k in env if k.startswith(('_PYI_', '_MEI', 'PYTHON'))]
    for k in keys_to_del:
        env.pop(k, None)
    if extra_env:
        env.update(extra_env)
    return env


def get_python_exe():
    cfg = load_config()
    custom_py = cfg.get('python_path', '').strip()
    if custom_py and os.path.isfile(custom_py):
        return custom_py

    embedded_candidates = [
        os.path.join(SERVER_DIR, 'python', 'python.exe'),
        os.path.join(BASE_DIR, 'python', 'python.exe'),
    ]
    for emb in embedded_candidates:
        if os.path.isfile(emb):
            return emb

    if not getattr(sys, 'frozen', False):
        return sys.executable

    for cmd in ('python', 'python3'):
        p = shutil.which(cmd)
        if p and os.path.isfile(p):
            if p.lower().endswith('fo3_launcher.exe'):
                continue
            return p

    patterns = [
        os.path.expandvars('%LOCALAPPDATA%\\Programs\\Python\\Python*\\python.exe'),
        'C:\\Python*\\python.exe',
        'C:\\Program Files\\Python*\\python.exe',
        'C:\\Program Files (x86)\\Python*\\python.exe',
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if not matches:
            continue
        matches.sort(reverse=True)
        for m in matches:
            if os.path.isfile(m):
                return m

    py_launcher = shutil.which('py')
    if py_launcher:
        return py_launcher

    return 'python'


def is_port_listening(port=8088, host='127.0.0.1'):
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


class ServerManager:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback if log_callback else lambda text: print(text)
        self.process = None
        self.is_active = False

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def kill_existing_processes(self):
        try:
            cmd = "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'start_all\\.py|http_config\\.py|messenger\\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            subprocess.run(
                ['powershell', '-NoProfile', '-Command', cmd],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
        except Exception as e:
            self.log(f'[เซิร์ฟเวอร์] ล้างโปรเซสเก่าผิดพลาด: {e}')

    def check_cryptography(self, py_exe):
        clean_env = get_clean_py_env()
        try:
            res = subprocess.run(
                [py_exe, '-c', 'import cryptography'],
                capture_output=True,
                env=clean_env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

        self.log('[เซิร์ฟเวอร์] กำลังติดตั้งไลบรารี cryptography อัตโนมัติ...')
        wheels_dir = os.path.join(SERVER_DIR, 'wheels')
        try:
            if os.path.exists(wheels_dir):
                subprocess.run(
                    [py_exe, '-m', 'pip', 'install', 'cryptography', '--no-index', f'--find-links={wheels_dir}'],
                    capture_output=True,
                    env=clean_env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                )

            res = subprocess.run(
                [py_exe, '-c', 'import cryptography'],
                capture_output=True,
                env=clean_env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

        try:
            subprocess.run(
                [py_exe, '-m', 'pip', 'install', 'cryptography'],
                capture_output=True,
                env=clean_env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )

            res = subprocess.run(
                [py_exe, '-c', 'import cryptography'],
                capture_output=True,
                env=clean_env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            return res.returncode == 0
        except Exception as e:
            self.log(f'[เซิร์ฟเวอร์] ติดตั้งไลบรารี cryptography ผิดพลาด: {e}')
            return False

    def _read_stream(self, stream):
        try:
            for line in iter(stream.readline, ''):
                if not line:
                    break
                line_str = line.strip()
                if not line_str:
                    continue
                self.log(f'[เซิร์ฟเวอร์] {line_str}')
        except Exception:
            pass
        finally:
            stream.close()

    def start_server(self, game_dir):
        if self.is_running():
            self.log('[เซิร์ฟเวอร์] เซิร์ฟเวอร์ FO3 กำลังทำงานอยู่แล้ว')
            return True

        py_exe = get_python_exe()

        clean_env = get_clean_py_env()
        try:
            test_py = subprocess.run(
                [py_exe, '--version'],
                capture_output=True,
                env=clean_env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            if test_py.returncode != 0:
                self.log(f'[เซิร์ฟเวอร์ผิดพลาด] รันคำสั่ง Python ไม่สำเร็จ ({py_exe})!')
                return False
        except Exception as e:
            self.log(f'[เซิร์ฟเวอร์ผิดพลาด] ไม่พบ Python บนเครื่อง: {e}')
            self.log("[คำแนะนำ] กรุณาติดตั้ง Python 3 และติ๊กเลือก 'Add Python to PATH' ตอนติดตั้ง หรือตั้งค่า path ของ python_path ใน config.json")
            return False

        if not self.check_cryptography(py_exe):
            self.log('[ผิดพลาด] ไลบรารี cryptography ยังไม่ได้ติดตั้ง!')
            return False

        self.log('[เซิร์ฟเวอร์] กำลังตรวจสอบและล้างโปรเซสเก่า...')
        self.kill_existing_processes()

        env = get_clean_py_env({
            'FO3_GAME': game_dir,
            'FO3_LANGUAGE': 'eng',
            'PYTHONUNBUFFERED': '1',
        })

        start_all_script = os.path.join(SERVER_DIR, 'start_all.py')
        if not os.path.isfile(start_all_script):
            self.log(f'[ผิดพลาด] ไม่พบไฟล์ {start_all_script}!')
            return False

        try:
            self.log('[เซิร์ฟเวอร์] กำลังเริ่มเซิร์ฟเวอร์ FO3 ในเบื้องหลัง...')
            self.process = subprocess.Popen(
                [py_exe, '-u', start_all_script],
                cwd=SERVER_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            self.is_active = True

            reader_thread = threading.Thread(target=self._read_stream, args=(self.process.stdout,), daemon=True)
            reader_thread.start()

            self.log('[เซิร์ฟเวอร์] เซิร์ฟเวอร์ FO3 เริ่มทำงานสำเร็จแล้ว!')
            return True
        except Exception as e:
            self.log(f'[ผิดพลาด] เริ่มเซิร์ฟเวอร์ไม่สำเร็จ: {e}')
            self.is_active = False
            return False

    def stop_server(self):
        self.log('[เซิร์ฟเวอร์] กำลังปิดเซิร์ฟเวอร์ FO3...')
        self.is_active = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.kill_existing_processes()
        self.process = None
        self.log('[เซิร์ฟเวอร์] เซิร์ฟเวอร์ FO3 หยุดทำงานแล้ว')

    def is_running(self):
        if self.process and self.process.poll() is None:
            return True
        if self.is_active:
            return True
        if is_port_listening(8088):
            return True
        return False
