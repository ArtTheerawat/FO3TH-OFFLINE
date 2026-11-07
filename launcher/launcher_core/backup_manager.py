from datetime import datetime
import json
import os
import shutil
import zipfile

from .config import BASE_DIR

GAMEDATA_DIR = os.path.join(BASE_DIR, 'Server', 'gamedata')
BACKUPS_DIR = os.path.join(BASE_DIR, 'Backups')


def open_gamedata_folder():
    if not os.path.exists(GAMEDATA_DIR):
        os.makedirs(GAMEDATA_DIR, exist_ok=True)
    os.startfile(GAMEDATA_DIR)


def open_backups_folder():
    if not os.path.exists(BACKUPS_DIR):
        os.makedirs(BACKUPS_DIR, exist_ok=True)
    os.startfile(BACKUPS_DIR)


def list_backups():
    if not os.path.exists(BACKUPS_DIR):
        return []

    items = []
    for f in os.listdir(BACKUPS_DIR):
        if not f.endswith('.zip'):
            continue
        p = os.path.join(BACKUPS_DIR, f)
        size_mb = os.path.getsize(p) / 1048576
        mtime = datetime.fromtimestamp(os.path.getmtime(p)).strftime('%d/%m/%Y %H:%M')
        items.append({
            'name': f,
            'path': p,
            'size_mb': f'{size_mb:.2f} MB',
            'time': mtime,
        })

    items.sort(key=lambda x: x['time'], reverse=True)
    return items


def backup_save(log_func=print):
    if not os.path.exists(GAMEDATA_DIR):
        return False, 'ไม่พบโฟลเดอร์ gamedata!'

    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUPS_DIR, f'fo3_save_backup_{timestamp}.zip')

    try:
        log_func('[สำรอง] กำลังบีบอัดข้อมูลเซฟ...')
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(GAMEDATA_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, GAMEDATA_DIR)
                    zipf.write(file_path, arcname)

        log_func(f'[สำรอง] สร้างไฟล์สำรองสำเร็จที่:\n{backup_file}')
        return True, backup_file
    except Exception as e:
        log_func(f'[สำรอง] สำรองข้อมูลผิดพลาด: {e}')
        return False, str(e)


def restore_save(src_path, log_func=print):
    if not os.path.exists(src_path):
        return False, 'ไม่พบไฟล์หรือโฟลเดอร์ต้นทาง!'

    backup_save(log_func)

    try:
        if os.path.isfile(src_path) and (src_path.endswith('.zip') or src_path.endswith('.rar')):
            if src_path.endswith('.zip'):
                log_func(f'[กู้คืน] กำลังแตกไฟล์ {src_path} ลง gamedata...')
                with zipfile.ZipFile(src_path, 'r') as zipf:
                    zipf.extractall(GAMEDATA_DIR)
                log_func('[กู้คืน] กู้คืนเซฟจาก ZIP สำเร็จแล้ว!')
                return True, 'กู้คืนสำเร็จ!'
            else:
                return False, 'กรุณาเลือกไฟล์บีบอัดนามสกุล .ZIP'
        elif os.path.isdir(src_path):
            log_func(f'[กู้คืน] กำลังคัดลอกจาก {src_path} ลง gamedata...')
            for item in os.listdir(src_path):
                s = os.path.join(src_path, item)
                d = os.path.join(GAMEDATA_DIR, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            log_func('[กู้คืน] คัดลอกข้อมูลเซฟสำเร็จแล้ว!')
            return True, 'กู้คืนสำเร็จ!'
        else:
            return False, 'รูปแบบไฟล์ไม่รองรับ!'
    except Exception as e:
        log_func(f'[กู้คืน] ผิดพลาด: {e}')
        return False, str(e)


def auto_recover_lost_coaches(log_func=print):
    state_file = os.path.join(GAMEDATA_DIR, 'state.json')

    has_active_coaches = False
    if os.path.isfile(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                cur_data = json.load(f)
            cur_coaches = cur_data.get('coaches', [])
            if isinstance(cur_coaches, list) and len(cur_coaches) > 0:
                has_active_coaches = True
        except Exception:
            pass

    if has_active_coaches:
        return False, [], None

    if not os.path.exists(BACKUPS_DIR):
        return False, [], None

    zip_candidates = []
    for f in os.listdir(BACKUPS_DIR):
        if not f.lower().endswith('.zip'):
            continue
        p = os.path.join(BACKUPS_DIR, f)
        if os.path.isfile(p):
            zip_candidates.append((p, os.path.getmtime(p)))

    zip_candidates.sort(key=lambda x: x[1], reverse=True)

    for zip_path, _ in zip_candidates:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                target_state_name = None
                for name in zf.namelist():
                    norm_name = name.replace('\\', '/')
                    if norm_name.endswith('state.json'):
                        target_state_name = name
                        break

                if not target_state_name:
                    continue

                raw_state = zf.read(target_state_name).decode('utf-8')
                bk_data = json.loads(raw_state)
                bk_coaches = bk_data.get('coaches', [])
                if isinstance(bk_coaches, list) and len(bk_coaches) > 0:
                    coach_names = [c.get('name') for c in bk_coaches if c.get('name')]
                    if not coach_names:
                        coach_names = [f"ผู้จัดการทีม Slot {c.get('slot', i)}" for i, c in enumerate(bk_coaches)]

                    zip_name = os.path.basename(zip_path)
                    log_func(f'[กู้ฉุกเฉิน] พบข้อมูลผู้จัดการทีม ({", ".join(coach_names)}) ในไฟล์สำรอง: {zip_name}')
                    log_func('[กู้ฉุกเฉิน] กำลังดำเนินการกู้คืนข้อมูลผู้จัดการทีมอัตโนมัติ...')

                    backup_save(log_func)

                    zf.extractall(GAMEDATA_DIR)
                    log_func(f'[กู้ฉุกเฉิน] ✅ กู้คืนผู้จัดการทีมสำเร็จ {len(coach_names)} คน ({", ".join(coach_names)})!')
                    return True, coach_names, zip_name
        except Exception:
            continue

    return False, [], None


def manual_recover_coaches(log_func=print):
    if not os.path.exists(BACKUPS_DIR):
        return False, 'ไม่พบโฟลเดอร์ Backups หรือยังไม่มีไฟล์สำรองใด ๆ!'

    zip_candidates = []
    for f in os.listdir(BACKUPS_DIR):
        if not f.lower().endswith('.zip'):
            continue
        p = os.path.join(BACKUPS_DIR, f)
        if os.path.isfile(p):
            zip_candidates.append((p, os.path.getmtime(p)))

    zip_candidates.sort(key=lambda x: x[1], reverse=True)

    if not zip_candidates:
        return False, 'ยังไม่มีไฟล์สำรองใด ๆ ในโฟลเดอร์ Backups!'

    for zip_path, _ in zip_candidates:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                target_state_name = None
                for name in zf.namelist():
                    norm_name = name.replace('\\', '/')
                    if norm_name.endswith('state.json'):
                        target_state_name = name
                        break

                if not target_state_name:
                    continue

                raw_state = zf.read(target_state_name).decode('utf-8')
                bk_data = json.loads(raw_state)
                bk_coaches = bk_data.get('coaches', [])
                if isinstance(bk_coaches, list) and len(bk_coaches) > 0:
                    coach_names = [c.get('name') for c in bk_coaches if c.get('name')]
                    if not coach_names:
                        coach_names = [f"ผู้จัดการทีม Slot {c.get('slot', i)}" for i, c in enumerate(bk_coaches)]

                    zip_name = os.path.basename(zip_path)
                    log_func(f'[กู้คืน] กำลังกู้คืนผู้จัดการทีม {len(coach_names)} คน จาก {zip_name}...')

                    backup_save(log_func)

                    zf.extractall(GAMEDATA_DIR)
                    msg = f'กู้คืนผู้จัดการทีมสำเร็จ {len(coach_names)} คน ({", ".join(coach_names)}) จากไฟล์สำรอง: {zip_name}!'
                    log_func(f'[กู้คืน] {msg}')
                    return True, msg
        except Exception as e:
            continue

    return False, 'ไม่พบข้อมูลผู้จัดการทีมใด ๆ ในไฟล์สำรองเดิม!'


def reset_database(log_func=print):
    candidates = [
        os.path.join(GAMEDATA_DIR, 'fifadb.zip'),
        os.path.join(BASE_DIR, 'fifadb.zip'),
        os.path.join(BASE_DIR, 'Server', 'gamedata', 'fifadb.zip'),
    ]
    zip_path = None
    for p in candidates:
        if os.path.exists(p):
            zip_path = p
            break

    if not zip_path:
        msg = 'ไม่พบไฟล์ต้นฉบับ fifadb.zip ในโฟลเดอร์ Server/gamedata!'
        log_func(f'[รีเซ็ต] ผิดพลาด: {msg}')
        return False, msg

    try:
        log_func('[รีเซ็ต] กำลังสร้างไฟล์สำรองความปลอดภัยสำหรับข้อมูลปัจจุบัน...')
        backup_save(log_func)

        for extra in ('fifadb.sqlite-wal', 'fifadb.sqlite-shm', 'fifadb.sqlite-journal'):
            extra_p = os.path.join(GAMEDATA_DIR, extra)
            if os.path.exists(extra_p):
                try:
                    os.remove(extra_p)
                except Exception:
                    pass

        log_func(f'[รีเซ็ต] กำลังแตกไฟล์ fifadb.sqlite ต้นฉบับจาก {os.path.basename(zip_path)}...')
        os.makedirs(GAMEDATA_DIR, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            if 'fifadb.sqlite' in zf.namelist():
                zf.extract('fifadb.sqlite', GAMEDATA_DIR)
            else:
                target_names = [n for n in zf.namelist() if n.endswith('fifadb.sqlite')]
                if target_names:
                    extracted_path = zf.extract(target_names[0], GAMEDATA_DIR)
                    final_path = os.path.join(GAMEDATA_DIR, 'fifadb.sqlite')
                    if os.path.abspath(extracted_path) != os.path.abspath(final_path):
                        shutil.move(extracted_path, final_path)
                else:
                    return False, 'ไม่พบไฟล์ fifadb.sqlite อยู่ใน fifadb.zip!'

        state_file = os.path.join(GAMEDATA_DIR, 'state.json')

        default_state = {
            'coaches': [],
            'defaultcoachid': '',
            'teams': {},
            'option': {
                'cameraOption': {
                    'kind': 1,
                    'custom': 1,
                    'height': 10,
                    'zoom': 10,
                },
            },
        }

        with open(state_file, 'w', encoding='utf-8') as sf:
            json.dump(default_state, sf, indent=2)

        log_func('[รีเซ็ต] ล้างข้อมูลผู้จัดการทีมและทีมทั้งหมดแล้ว (state.json)')
        log_func('[รีเซ็ต] ล้างข้อมูลสำเร็จ! เมื่อเข้าเกมคุณจะได้สร้างผู้จัดการทีมใหม่ตั้งแต่ต้น')
        return True, 'ล้างข้อมูลสำเร็จ!'
    except Exception as e:
        log_func(f'[รีเซ็ต] ผิดพลาดระหว่างรีเซ็ต: {e}')
        return False, str(e)


def ensure_state_file(log_func=print):
    os.makedirs(GAMEDATA_DIR, exist_ok=True)
    state_file = os.path.join(GAMEDATA_DIR, 'state.json')

    need_create = False
    if not os.path.isfile(state_file):
        need_create = True
    else:
        try:
            with open(state_file, 'r', encoding='utf-8') as sf:
                st = json.load(sf)
            if not isinstance(st, dict):
                need_create = True
        except Exception:
            need_create = True

    if need_create:
        default_state = {
            'coaches': [],
            'defaultcoachid': '',
            'teams': {},
            'option': {
                'cameraOption': {
                    'kind': 1,
                    'custom': 1,
                    'height': 10,
                    'zoom': 10,
                },
            },
        }

        try:
            with open(state_file, 'w', encoding='utf-8') as sf:
                json.dump(default_state, sf, indent=2)
            log_func('[ระบบ] พบว่า state.json ขาดหายไป ระบบสร้างไฟล์เปล่ามาตรฐานขึ้นใหม่อัตโนมัติแล้ว พร้อมสำหรับการสร้างผู้จัดการทีมใหม่')
            return True
        except Exception as e:
            log_func(f'[ระบบ] แจ้งเตือนการสร้าง state.json: {e}')
    return False
