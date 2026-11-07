# FO3_Launcher.py — reconstructed from CPython 3.15 disassembly
try:
    import pyi_splash
    pyi_splash.update_text('กำลังโหลดการตั้งค่าและหน้าจอ FO3 Offline...')
except Exception:
    pass

from datetime import datetime
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import webbrowser
import customtkinter as ctk
from PIL import Image

from launcher_core.backup_manager import (
    auto_recover_lost_coaches,
    backup_save,
    ensure_state_file,
    manual_recover_coaches,
    open_backups_folder,
    open_gamedata_folder,
    restore_save,
    reset_database
)
from launcher_core.config import (
    BASE_DIR,
    get_game_path,
    load_config,
    save_config,
    set_game_path
)
from launcher_core.game_manager import (
    auto_detect_game,
    check_game_dir,
    deep_scan_game_drives,
    launch_game,
    quick_detect_game,
    setup_game_files
)
from launcher_core.hosts_manager import install_hosts, is_hosts_configured, open_hosts_in_notepad
from launcher_core.server_manager import ServerManager
from launcher_core.updater import apply_setup_update, apply_zip_update, check_for_updates, download_file

THEME = {
    'bg_window': '#F8FAFC',
    'bg_card': '#FFFFFF',
    'border': '#E2E8F0',
    'text_dark': '#0F172A',
    'text_gray': '#475569',
    'green': '#10B981',
    'green_hover': '#059669',
    'red': '#EF4444',
    'red_hover': '#DC2626',
    'blue': '#2563EB',
    'blue_hover': '#1D4ED8',
    'zalo': '#0068FF',
    'zalo_hover': '#0052CC',
    'facebook': '#1877F2',
    'facebook_hover': '#0D65D9',
    'console_bg': '#0F172A',
    'console_text': '#F1F5F9'
}


class SimpleFO3Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config = load_config()
        self.app_name = self.config.get('app_name', 'FO3 Offline')
        self.version = self.config.get('version', '1.0.0')
        self.author = self.config.get('author', 'FO3TH OFFLINE')
        self.zalo_link = self.config.get('zalo_link', 'https://zalo.me/0905020696')
        self.zalo_phone = self.config.get('zalo_phone', '0905.020.696')
        self.fb_group_link = self.config.get('fb_group_link', 'https://www.facebook.com/groups/congdongfo3vietnam')
        self.bank_name = self.config.get('bank_name', 'Vietcombank')
        self.bank_account_name = self.config.get('bank_account_name', 'TRINH NHU Y')
        self.stk = self.config.get('bank_account_number', '0431000215103')
        self.logo_file = self.config.get('logo_image_file', 'images/logo_fo3.png')
        self.qr_file = self.config.get('qr_image_file', 'images/donate_qr.jpg')

        ctk.set_appearance_mode('light')
        self.title(f'{self.app_name} — v{self.version}')
        self.geometry('900x640')
        self.minsize(880, 580)
        self.configure(fg_color=THEME['bg_window'])

        icon_path = self.resolve_asset_path('images/app_icon.ico')
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.log_file_path = os.path.join(BASE_DIR, 'server_log.txt')
        self.server_mgr = ServerManager(log_callback=self.log_message)

        self.game_dir = quick_detect_game()

        self._build_ui()
        self._update_game_state_ui()

        try:
            import pyi_splash
            pyi_splash.close()
        except Exception:
            pass

        self.log_message('เซฟแยกเฉพาะเวอร์ชันนี้ เล่นได้แม้ไม่มีอินเทอร์เน็ต')
        self.log_message("กดปุ่ม '▶ เข้าเกม' สีเขียวเพื่อเริ่มเข้าเกม")
        if self.game_dir:
            self.log_message(f'โฟลเดอร์เกม: {self.game_dir}')
        else:
            self.log_message('[เกม] ยังไม่พบโฟลเดอร์เกม กำลังสแกนไดรฟ์ทั้งหมดโดยอัตโนมัติ...')
            threading.Thread(target=self._async_scan_game_drives, daemon=True).start()

        self.protocol('WM_DELETE_WINDOW', self.on_closing)

        ensure_state_file(self.log_message)

        self.after(1000, lambda: self.action_check_update(silent=True))

    def _async_scan_game_drives(self):
        found = deep_scan_game_drives(progress_callback=self.log_message)
        if found:
            def on_found():
                self.game_dir = found
                self._update_game_state_ui()
                self.log_message(f'[เกม] ✅ พบโฟลเดอร์เกมอัตโนมัติ: {found}')
            self.after(0, on_found)
        else:
            self.log_message("[เกม] ไม่พบโฟลเดอร์ที่มี fifazf.exe กรุณากด 'เลือกเกม' ด้านบน.")

    def resolve_asset_path(self, rel_path):
        if hasattr(sys, '_MEIPASS'):
            p = os.path.join(sys._MEIPASS, rel_path)
            if os.path.exists(p):
                return p
        p = os.path.join(BASE_DIR, rel_path)
        if os.path.exists(p):
            return p
        p_img = os.path.join(BASE_DIR, 'images', os.path.basename(rel_path))
        if os.path.exists(p_img):
            return p_img
        p_root = os.path.join(BASE_DIR, os.path.basename(rel_path))
        if os.path.exists(p_root):
            return p_root
        return p

    def _build_ui(self):
        # ---- กรอบด้านบน: โลโก้ + ข้อมูล ----
        top_frame = ctk.CTkFrame(self, fg_color=THEME['bg_card'], corner_radius=10, border_width=1, border_color=THEME['border'])
        top_frame.pack(fill='x', padx=16, pady=(16, 10))

        title_box = ctk.CTkFrame(top_frame, fg_color='transparent')
        title_box.pack(fill='x', padx=16, pady=(10, 2))

        logo_path = self.resolve_asset_path(self.logo_file)
        if os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path)

                ctk_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(146, 40))
                lbl_logo = ctk.CTkLabel(title_box, image=ctk_logo, text='')
                lbl_logo.pack(side='left', padx=(0, 10))
            except Exception:
                pass

        lbl_title = ctk.CTkLabel(
            title_box,
            text=f'{self.app_name} — เวอร์ชัน {self.version}',
            font=ctk.CTkFont(family='Segoe UI', size=22, weight='bold'),
            text_color=THEME['text_dark']
        )
        lbl_title.pack(side='left')

        self.lbl_path = ctk.CTkLabel(
            top_frame,
            text=f"โฟลเดอร์เกม: {self.game_dir if self.game_dir else 'ยังไม่ได้เลือกโฟลเดอร์'}",
            font=ctk.CTkFont(family='Segoe UI', size=13),
            text_color='#0284C7' if self.game_dir else THEME['red']
        )
        self.lbl_path.pack(anchor='w', padx=16, pady=(0, 2))

        info_row = ctk.CTkFrame(top_frame, fg_color='transparent')
        info_row.pack(fill='x', padx=16, pady=(0, 10))

        lbl_author = ctk.CTkLabel(
            info_row,
            text=f'ผู้พัฒนา: {self.author} • ติดต่อ Zalo: {self.zalo_phone}',
            font=ctk.CTkFont(family='Segoe UI', size=12),
            text_color=THEME['text_gray']
        )
        lbl_author.pack(side='left')

        self.lbl_server_status = ctk.CTkLabel(
            info_row,
            text='เซิร์ฟเวอร์: ปิดอยู่ ●',
            font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
            text_color=THEME['red']
        )
        self.lbl_server_status.pack(side='right')

        # ---- กรอบปุ่มกด ----
        btn_frame = ctk.CTkFrame(self, fg_color=THEME['bg_card'], corner_radius=10, border_width=1, border_color=THEME['border'])
        btn_frame.pack(fill='x', padx=16, pady=(0, 10))

        self.btn_play = ctk.CTkButton(
            btn_frame,
            text='▶  เข้าเกม',
            font=ctk.CTkFont(family='Segoe UI', size=15, weight='bold'),
            height=44,
            corner_radius=8,
            fg_color=THEME['green'],
            hover_color=THEME['green_hover'],
            command=self.toggle_play_server
        )
        self.btn_play.pack(side='left', padx=(12, 6), pady=10, expand=True, fill='x')

        self.btn_select = ctk.CTkButton(
            btn_frame,
            text='📁  เลือกเกม',
            font=ctk.CTkFont(family='Segoe UI', size=13),
            height=44,
            corner_radius=8,
            fg_color='#F1F5F9',
            text_color=THEME['text_dark'],
            hover_color=THEME['border'],
            command=self.action_select_game
        )
        self.btn_select.pack(side='left', padx=4, pady=10, expand=True, fill='x')

        self.btn_admin = ctk.CTkButton(
            btn_frame,
            text='🌐  ผู้ดูแลเว็บ',
            font=ctk.CTkFont(family='Segoe UI', size=13),
            height=44,
            corner_radius=8,
            fg_color='#F1F5F9',
            text_color=THEME['text_dark'],
            hover_color=THEME['border'],
            state='disabled',
            command=self.action_open_admin
        )
        self.btn_admin.pack(side='left', padx=4, pady=10, expand=True, fill='x')

        self.btn_save = ctk.CTkButton(
            btn_frame,
            text='💾  สำรองเซฟ',
            font=ctk.CTkFont(family='Segoe UI', size=13),
            height=44,
            corner_radius=8,
            fg_color='#F1F5F9',
            text_color=THEME['text_dark'],
            hover_color=THEME['border'],
            command=self.action_backup_menu
        )
        self.btn_save.pack(side='left', padx=3, pady=10, expand=True, fill='x')

        self.btn_reset = ctk.CTkButton(
            btn_frame,
            text='♻️  รีเซ็ตข้อมูล',
            font=ctk.CTkFont(family='Segoe UI', size=13),
            height=44,
            corner_radius=8,
            fg_color='#F1F5F9',
            text_color='#DC2626',
            hover_color='#FEE2E2',
            command=self.action_reset_data
        )
        self.btn_reset.pack(side='left', padx=3, pady=10, expand=True, fill='x')

        self.btn_update = ctk.CTkButton(
            btn_frame,
            text='🔄  อัพเดต',
            font=ctk.CTkFont(family='Segoe UI', size=13),
            height=44,
            corner_radius=8,
            fg_color='#F1F5F9',
            text_color=THEME['text_dark'],
            hover_color=THEME['border'],
            command=lambda: self.action_check_update(silent=False)
        )
        self.btn_update.pack(side='left', padx=(3, 12), pady=10, expand=True, fill='x')

        # ---- กรอบด้านล่าง: บริจาค + บันทึกการทำงาน ----
        bottom_box = ctk.CTkFrame(self, fg_color='transparent')
        bottom_box.pack(fill='both', expand=True, padx=16, pady=(0, 16))
        bottom_box.grid_columnconfigure(0, weight=0, minsize=260)
        bottom_box.grid_columnconfigure(1, weight=1)
        bottom_box.grid_rowconfigure(0, weight=1)

        donate_card = ctk.CTkFrame(bottom_box, fg_color=THEME['bg_card'], corner_radius=10, border_width=1, border_color=THEME['border'])
        donate_card.grid(row=0, column=0, sticky='nsew', padx=(0, 8))

        ctk.CTkLabel(
            donate_card,
            text='💖  สนับสนุนผู้พัฒนา',
            font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
            text_color=THEME['text_dark']
        ).pack(pady=(10, 4))

        qr_path = self.resolve_asset_path(self.qr_file)
        if os.path.exists(qr_path):
            try:
                pil_img = Image.open(qr_path)

                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(150, 168))
                lbl_qr = ctk.CTkLabel(donate_card, image=ctk_img, text='')
                lbl_qr.pack(pady=2)
            except Exception:
                pass

        ctk.CTkLabel(
            donate_card,
            text=f'STK: {self.stk}\n{self.bank_name} - {self.bank_account_name}',
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
            text_color=THEME['text_dark'],
            justify='center'
        ).pack(pady=(2, 6))

        btn_copy_stk = ctk.CTkButton(
            donate_card,
            text='📋  คัดลอกเลขบัญชี',
            height=28,
            font=ctk.CTkFont(family='Segoe UI', size=11),
            fg_color='#F1F5F9',
            text_color=THEME['text_dark'],
            hover_color=THEME['border'],
            command=self.copy_stk
        )
        btn_copy_stk.pack(fill='x', padx=16, pady=(0, 6))

        btn_zalo = ctk.CTkButton(
            donate_card,
            text='💬  แชทผ่าน Zalo',
            height=30,
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
            fg_color=THEME['zalo'],
            hover_color=THEME['zalo_hover'],
            command=lambda: webbrowser.open(self.zalo_link)
        )
        btn_zalo.pack(fill='x', padx=16, pady=(0, 6))

        btn_fb = ctk.CTkButton(
            donate_card,
            text='👥  กลุ่ม FB ช่วยเหลือ',
            height=30,
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
            fg_color=THEME['facebook'],
            hover_color=THEME['facebook_hover'],
            command=lambda: webbrowser.open(self.fb_group_link)
        )
        btn_fb.pack(fill='x', padx=16, pady=(0, 10))

        log_card = ctk.CTkFrame(bottom_box, fg_color=THEME['bg_card'], corner_radius=10, border_width=1, border_color=THEME['border'])
        log_card.grid(row=0, column=1, sticky='nsew', padx=(8, 0))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        log_head = ctk.CTkFrame(log_card, fg_color='transparent')
        log_head.grid(row=0, column=0, sticky='ew', padx=12, pady=(10, 4))

        ctk.CTkLabel(
            log_head,
            text='📋  การแจ้งเตือน & บันทึกการทำงาน',
            font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
            text_color=THEME['text_dark']
        ).pack(side='left')

        btn_clear = ctk.CTkButton(
            log_head,
            text='ล้างบันทึก',
            width=60,
            height=24,
            font=ctk.CTkFont(family='Segoe UI', size=11),
            fg_color='#F1F5F9',
            text_color=THEME['text_dark'],
            hover_color=THEME['border'],
            command=self.clear_log
        )
        btn_clear.pack(side='right')

        btn_open_log = ctk.CTkButton(
            log_head,
            text='📄  เปิดไฟล์บันทึก',
            width=85,
            height=24,
            font=ctk.CTkFont(family='Segoe UI', size=11),
            fg_color='#F1F5F9',
            text_color=THEME['text_dark'],
            hover_color=THEME['border'],
            command=self.open_log_file
        )
        btn_open_log.pack(side='right', padx=(0, 6))

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            fg_color=THEME['console_bg'],
            text_color=THEME['console_text'],
            font=ctk.CTkFont(family='Consolas', size=12),
            wrap='word',
            corner_radius=6
        )
        self.log_textbox.grid(row=1, column=0, sticky='nsew', padx=12, pady=(0, 12))

    def _update_game_state_ui(self):
        is_valid = bool(self.game_dir) and check_game_dir(self.game_dir)

        if is_valid:
            self.lbl_path.configure(
                text=f'โฟลเดอร์เกม: {self.game_dir}',
                text_color='#0284C7'
            )
            if self.server_mgr.is_running():
                self.btn_play.configure(state='normal', text='⏹  หยุดเซิร์ฟเวอร์', fg_color=THEME['red'], hover_color=THEME['red_hover'])
                self.lbl_server_status.configure(text='เซิร์ฟเวอร์: กำลังทำงาน ●', text_color=THEME['green'])
            else:
                self.btn_play.configure(state='normal', text='▶  เข้าเกม', fg_color=THEME['green'], hover_color=THEME['green_hover'])
                self.lbl_server_status.configure(text='เซิร์ฟเวอร์: ปิดอยู่ ●', text_color=THEME['red'])
        else:
            self.lbl_path.configure(
                text="โฟลเดอร์เกม: ยังไม่ได้เลือกโฟลเดอร์ที่มี fifazf.exe (กด 'เลือกเกม' ด้านล่าง)",
                text_color=THEME['red']
            )
            self.btn_play.configure(state='disabled', text='⚠️  ยังไม่ได้เลือกเกม (fifazf.exe)', fg_color='#94A3B8')

        if self.server_mgr.is_running():
            self.btn_admin.configure(state='normal')
        else:
            self.btn_admin.configure(state='disabled')

    def log_message(self, message):
        ts = datetime.now().strftime('[%H:%M:%S] ')
        formatted = f'{ts}{message}\n'

        def append():
            self.log_textbox.configure(state='normal')
            self.log_textbox.insert('end', formatted)
            self.log_textbox.see('end')
            self.log_textbox.configure(state='disabled')

        self.after(0, append)
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(formatted)
        except Exception:
            pass

    def open_log_file(self):
        try:
            if not os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== บันทึกการทำงาน FO3 Offline ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
            os.startfile(self.log_file_path)
        except Exception as e:
            self.log_message(f'เปิดไฟล์บันทึกไม่ได้: {e}')

    def clear_log(self):
        self.log_textbox.configure(state='normal')
        self.log_textbox.delete('1.0', 'end')
        self.log_textbox.configure(state='disabled')

    def copy_stk(self):
        self.clipboard_clear()
        self.clipboard_append(self.stk)
        messagebox.showinfo('คัดลอกแล้ว', f'คัดลอกเลขบัญชีแล้ว: {self.stk} ({self.bank_name} - {self.bank_account_name})!')

    def toggle_play_server(self):
        btn_text = self.btn_play.cget('text')

        if 'หยุด' in btn_text or self.server_mgr.is_running():
            self.btn_play.configure(state='disabled', text='⏳  กำลังหยุดเซิร์ฟเวอร์...')
            threading.Thread(target=self._stop_server_thread, daemon=True).start()
            return

        if not self.game_dir or not check_game_dir(self.game_dir):
            messagebox.showerror('ยังไม่ได้เลือกเกม', "กรุณากดปุ่ม 'เลือกเกม' เพื่อเลือกโฟลเดอร์ที่มี fifazf.exe!")
            self.action_select_game()
            return

        if not is_hosts_configured():
            ans = messagebox.askyesno('ติดตั้ง Hosts', 'ระบบต้องติดตั้ง Hosts (APSEODESK172) เพื่อเชื่อมต่อออฟไลน์\nต้องการติดตั้งอัตโนมัติหรือไม่?')
            if ans:
                self.action_install_hosts()

        threading.Thread(target=self._run_server_and_game_thread, daemon=True).start()

    def _stop_server_thread(self):
        self.server_mgr.stop_server()
        self.after(0, self._update_game_state_ui)

    def _run_server_and_game_thread(self):
        self.btn_play.configure(state='disabled', text='⏳  กำลังเริ่มระบบ...')
        success = self.server_mgr.start_server(self.game_dir)

        if success:
            self.after(0, lambda: self.btn_play.configure(
                state='normal',
                text='⏹  หยุดเซิร์ฟเวอร์',
                fg_color=THEME['red'],
                hover_color=THEME['red_hover']
            ))
            self.after(0, lambda: self.btn_admin.configure(state='normal'))
            self.after(0, lambda: self.lbl_server_status.configure(text='เซิร์ฟเวอร์: กำลังทำงาน ●', text_color=THEME['green']))

            self.log_message('[เกม] รอให้เซิร์ฟเวอร์เสถียร (3 วินาที)...')
            time.sleep(3)

            self.log_message('[เกม] กำลังเปิด fifalauncher_offline.exe...')
            ok, msg = launch_game(self.game_dir, self.log_message)
            if ok:
                self.log_message('[เกม] เปิดเกมสำเร็จ! ขอให้สนุกกับเกม')
                return

            self.log_message(f'[เกมผิดพลาด] {msg}')
            return

        self.after(0, self._update_game_state_ui)
        self.after(0, lambda: self.lbl_server_status.configure(text='เซิร์ฟเวอร์: การเริ่มระบบผิดพลาด ●', text_color=THEME['red']))

    def action_select_game(self):
        folder = filedialog.askdirectory(title='เลือกโฟลเดอร์เกม FIFA Online 3 (ที่มีไฟล์ fifazf.exe)')
        if not folder:
            return

        if check_game_dir(folder):
            self.game_dir = folder
            set_game_path(folder)
            self.log_message(f'เลือกโฟลเดอร์เกมแล้ว: {folder}')
            setup_game_files(folder, self.log_message)
            self._update_game_state_ui()
            messagebox.showinfo('สำเร็จ', f'บันทึกโฟลเดอร์เกมแล้ว:\n{folder}')
            return

        messagebox.showerror('โฟลเดอร์ผิดพลาด', "โฟลเดอร์ที่เลือกไม่มีไฟล์ 'fifazf.exe'!\nกรุณาเลือกโฟลเดอร์ที่ติดตั้งเกม FIFA Online 3 ให้ถูกต้อง")
        self._update_game_state_ui()

    def action_open_admin(self):
        if not self.server_mgr.is_running():
            messagebox.showwarning('ยังไม่ได้เปิดเซิร์ฟเวอร์', "กรุณากด 'เล่นออฟไลน์' เพื่อเริ่มเซิร์ฟเวอร์ก่อนเปิดผู้ดูแลเว็บ!")
            return

        url = self.config.get('admin_url', 'http://127.0.0.1:8088/')
        self.log_message(f'เปิดผู้ดูแลเว็บ: {url}')
        webbrowser.open(url)

    def action_install_hosts(self):
        ok, msg = install_hosts()
        self.log_message(f"[Hosts] {msg.splitlines()[0]}")
        if ok:
            messagebox.showinfo('ติดตั้ง Hosts', msg)
            return

        ans = messagebox.askyesno('ติดตั้ง Hosts', f'{msg}\n\nต้องการเปิดไฟล์ Hosts ด้วย Notepad (สิทธิ์ Admin) เพื่อเพิ่มบรรทัดนี้ท้ายไฟล์หรือไม่?\n127.0.0.1 APSEODESK172')
        if ans:
            open_hosts_in_notepad()

    def action_backup_menu(self):
        win = ctk.CTkToplevel(self)
        win.title('สำรอง & จัดการข้อมูล')
        win.geometry('380x305')
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text='จัดการเซฟเกม (gamedata)', font=ctk.CTkFont(family='Segoe UI', size=15, weight='bold')).pack(pady=(14, 10))

        btn_bk = ctk.CTkButton(
            win,
            text='📦  สร้างไฟล์สำรองใหม่ (.ZIP)',
            height=34,
            fg_color=THEME['green'],
            hover_color=THEME['green_hover'],
            command=lambda: [self._do_backup(), win.destroy()]
        )
        btn_bk.pack(fill='x', padx=30, pady=4)

        btn_restore = ctk.CTkButton(
            win,
            text='📥  กู้คืนจากไฟล์ ZIP เดิม',
            height=34,
            fg_color=THEME['blue'],
            hover_color=THEME['blue_hover'],
            command=lambda: [win.destroy(), self.action_import_save()]
        )
        btn_restore.pack(fill='x', padx=30, pady=4)

        btn_recover = ctk.CTkButton(
            win,
            text='🩺  กู้ฉุกเฉินข้อมูลผู้จัดการ (กู้คืนจากสำรอง)',
            height=34,
            fg_color='#FEF3C7',
            text_color='#B45309',
            hover_color='#FDE68A',
            command=lambda: [win.destroy(), self.action_recover_coaches()]
        )
        btn_recover.pack(fill='x', padx=30, pady=4)

        btn_reset = ctk.CTkButton(
            win,
            text='♻️  รีเซ็ตเป็นข้อมูลต้นฉบับ (จาก fifadb.zip)',
            height=34,
            fg_color='#FEE2E2',
            text_color='#DC2626',
            hover_color='#FECACA',
            command=lambda: [win.destroy(), self.action_reset_data()]
        )
        btn_reset.pack(fill='x', padx=30, pady=4)

        btn_open = ctk.CTkButton(
            win,
            text='📂  เปิดโฟลเดอร์ที่เก็บไฟล์เซฟ',
            height=34,
            fg_color='#F1F5F9',
            text_color=THEME['text_dark'],
            hover_color=THEME['border'],
            command=lambda: [open_gamedata_folder(), win.destroy()]
        )
        btn_open.pack(fill='x', padx=30, pady=4)

    def action_reset_data(self):
        if self.server_mgr.is_running():
            messagebox.showwarning('เซิร์ฟเวอร์กำลังทำงาน', "เซิร์ฟเวอร์หรือเกมกำลังทำงานอยู่!\n\nกรุณากด 'หยุดเซิร์ฟเวอร์' ก่อนรีเซ็ตข้อมูล เพื่อป้องกันไฟล์เสียหาย")
            return

        confirm = messagebox.askyesno('ยืนยันการรีเซ็ตข้อมูล', "คุณแน่ใจหรือไม่ว่าต้องการล้างข้อมูลเกมทั้งหมด?\n\n• ผู้จัดการทีม นักเตะ EP และข้อมูลที่สร้างไว้ทั้งหมดจะถูกคืนสู่สถานะต้นฉบับจาก fifadb.zip\n• ระบบจะสำรองข้อมูลไปที่โฟลเดอร์ Backups อัตโนมัติก่อนรีเซ็ต\n\nกด 'Yes' เพื่อทำต่อ หรือ 'No' เพื่อยกเลิก")
        if not confirm:
            return

        ok, msg = reset_database(self.log_message)
        if ok:
            messagebox.showinfo('รีเซ็ตข้อมูล', 'ล้างข้อมูลสำเร็จ!\nฐานข้อมูล fifadb.sqlite ถูกคืนสู่สถานะต้นฉบับแล้ว')
            return

        messagebox.showerror('รีเซ็ตไม่สำเร็จ', f'รีเซ็ตข้อมูลไม่ได้:\n{msg}')

    def _do_backup(self):
        ok, res = backup_save(self.log_message)
        if ok:
            messagebox.showinfo('สำรองข้อมูล', f'สำรองข้อมูลสำเร็จไปที่:\n{res}')
            return

        messagebox.showerror('สำรองข้อมูลไม่สำเร็จ', res)

    def action_import_save(self):
        file_path = filedialog.askopenfilename(title='เลือกไฟล์สำรอง (.ZIP)', filetypes=[('ZIP Archive', '*.zip')])
        if not file_path:
            return

        ok, msg = restore_save(file_path, self.log_message)
        if ok:
            messagebox.showinfo('สำเร็จ', 'กู้คืนเซฟเดิมสำเร็จ!')
            return

        messagebox.showerror('ผิดพลาด', msg)

    def action_recover_coaches(self):
        ok, msg = manual_recover_coaches(self.log_message)
        if ok:
            messagebox.showinfo('กู้คืนสำเร็จ', msg)
            return

        messagebox.showwarning('แจ้งเตือน', msg)

    def action_check_update(self, silent=False):
        if not silent:
            self.log_message('[อัพเดต] กำลังตรวจสอบเวอร์ชันใหม่จาก GitHub...')
        threading.Thread(target=lambda: self._check_update_thread(silent), daemon=True).start()

    def _check_update_thread(self, silent=False):
        repo = self.config.get('github_repo', '')
        has_update, new_ver, changelog, download_url, asset_name = check_for_updates(repo)

        if has_update:
            self.log_message(f'[อัพเดต] 🚀 พบเวอร์ชันใหม่: {new_ver} (บังคับให้อัพเดต)!')
            self.after(0, lambda: self._show_force_update_modal(new_ver, changelog, download_url, asset_name))
            return

        if not silent:
            self.log_message(f'[อัพเดต] {changelog}')
            self.after(0, lambda: messagebox.showinfo('อัพเดต', changelog))
            return

        self.log_message(f'[อัพเดต] คุณใช้เวอร์ชันล่าสุดอยู่แล้ว ({self.version}).')

    def _show_force_update_modal(self, new_ver, changelog, download_url, asset_name):
        modal = ctk.CTkToplevel(self)
        modal.title(f'อัพเดตบังคับ — FO3 Offline {new_ver}')
        modal.geometry('520x440')
        modal.minsize(500, 420)
        modal.configure(fg_color=THEME['bg_card'])
        modal.transient(self)
        modal.grab_set()

        icon_path = self.resolve_asset_path('images/app_icon.ico')
        if os.path.exists(icon_path):
            try:
                modal.iconbitmap(icon_path)
            except Exception:
                pass

        def on_modal_close():
            ans = messagebox.askyesno('ต้องอัพเดต', f'เวอร์ชัน {new_ver} เป็นอัพเดตบังคับเพื่อให้ระบบและข้อมูลเซิร์ฟเวอร์ทำงานเสถียร\n\nหากไม่อัพเดต คุณจะใช้ Launcher ต่อไม่ได้\n\nคุณแน่ใจหรือไม่ที่จะออกจากโปรแกรม?')
            if ans:
                if self.server_mgr.is_running():
                    self.server_mgr.stop_server()
                self.destroy()
                sys.exit(0)

        modal.protocol('WM_DELETE_WINDOW', on_modal_close)

        header_frame = ctk.CTkFrame(modal, fg_color='transparent')
        header_frame.pack(fill='x', padx=20, pady=(18, 8))

        ctk.CTkLabel(
            header_frame,
            text=f'🚀  พบเวอร์ชันใหม่: {new_ver}',
            font=ctk.CTkFont(family='Segoe UI', size=16, weight='bold'),
            text_color=THEME['blue']
        ).pack(anchor='w')

        ctk.CTkLabel(
            header_frame,
            text=f'เวอร์ชันปัจจุบัน: v{self.version}  ➜  เวอร์ชันล่าสุด: {new_ver}\n(*) เป็นอัพเดตบังคับ Launcher จะดาวน์โหลดและติดตั้งอัตโนมัติ',
            font=ctk.CTkFont(family='Segoe UI', size=12),
            text_color=THEME['text_gray'],
            justify='left'
        ).pack(anchor='w', pady=(4, 0))

        ctk.CTkLabel(
            modal,
            text='สิ่งที่อัพเดต:',
            font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
            text_color=THEME['text_dark']
        ).pack(anchor='w', padx=20, pady=(6, 2))

        txt_changelog = ctk.CTkTextbox(
            modal,
            height=130,
            corner_radius=8,
            fg_color='#F8FAFC',
            text_color=THEME['text_dark'],
            font=ctk.CTkFont(family='Segoe UI', size=11)
        )
        txt_changelog.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        txt_changelog.insert('1.0', changelog if changelog else 'อัพเดตฟีเจอร์และแก้บั๊ก')
        txt_changelog.configure(state='disabled')

        progress_frame = ctk.CTkFrame(modal, fg_color='transparent')
        progress_frame.pack(fill='x', padx=20, pady=(0, 12))

        lbl_status = ctk.CTkLabel(
            progress_frame,
            text='กำลังเตรียมดาวน์โหลดอัพเดต...',
            font=ctk.CTkFont(family='Segoe UI', size=12),
            text_color=THEME['text_dark']
        )
        lbl_status.pack(anchor='w')

        lbl_percent = ctk.CTkLabel(
            progress_frame,
            text='',
            font=ctk.CTkFont(family='Segoe UI', size=11),
            text_color=THEME['text_gray']
        )
        lbl_percent.pack(anchor='e', pady=(0, 2))

        progress_bar = ctk.CTkProgressBar(progress_frame, height=12, corner_radius=6)
        progress_bar.pack(fill='x', pady=(2, 6))
        progress_bar.set(0.0)

        btn_action = ctk.CTkButton(
            modal,
            text='⏬  กำลังดาวน์โหลดอัพเดตอัตโนมัติ...',
            font=ctk.CTkFont(family='Segoe UI', size=14, weight='bold'),
            height=40,
            corner_radius=8,
            fg_color=THEME['green'],
            hover_color=THEME['green_hover'],
            text_color='#FFFFFF'
        )
        btn_action.pack(fill='x', padx=20, pady=(0, 18))

        is_downloading = [False]

        def start_download():
            if is_downloading[0]:
                return
            is_downloading[0] = True
            btn_action.configure(state='disabled', text='⏳  กำลังดาวน์โหลดอัพเดต...', fg_color='#94A3B8')
            lbl_status.configure(text=f"กำลังโหลด {asset_name if asset_name else 'update.exe'}...")

            def download_worker():
                temp_dir = os.path.join(BASE_DIR, 'temp_update')
                os.makedirs(temp_dir, exist_ok=True)
                target_file = os.path.join(temp_dir, asset_name if asset_name else 'update.exe')

                def progress_cb(pct, downloaded, total):
                    val = pct / 100.0
                    down_mb = downloaded / 1048576
                    tot_mb = total / 1048576
                    try:
                        modal.after(0, lambda: [
                            progress_bar.set(val),
                            lbl_status.configure(text=f'กำลังดาวน์โหลดอัพเดต: {pct}%'),
                            lbl_percent.configure(text=f'{down_mb:.1f} MB / {tot_mb} MB')
                        ])
                    except Exception:
                        pass

                ok = download_file(download_url, target_file, progress_callback=progress_cb)

                if ok and os.path.exists(target_file):
                    try:
                        modal.after(0, lambda: [
                            progress_bar.set(1.0),
                            lbl_status.configure(text='✅ ดาวน์โหลดเสร็จ! กำลังปิด Launcher อัตโนมัติเพื่อติดตั้งทับ...'),
                            lbl_percent.configure(text='กำลังเตรียมติดตั้งเวอร์ชันใหม่...')
                        ])
                    except Exception:
                        pass

                    actual_setup_exe = None
                    try:
                        import zipfile
                        with zipfile.ZipFile(target_file, 'r') as zf:
                            for name in zf.namelist():
                                if name.lower().endswith('.exe') and ('setup' in name.lower() or 'fo3' in name.lower()):
                                    zf.extract(name, temp_dir)
                                    actual_setup_exe = os.path.join(temp_dir, name)
                                    break
                    except Exception as e:
                        self.log_message(f'[อัพเดต] ตรวจสอบแพ็ก ZIP ผิดพลาด: {e}')

                    if target_file.lower().endswith('.exe') or actual_setup_exe:
                        setup_to_run = actual_setup_exe if actual_setup_exe else target_file

                        def do_shutdown_and_install():
                            try:
                                if self.server_mgr.is_running():
                                    self.server_mgr.stop_server()
                            except Exception:
                                pass

                            ok_update = apply_setup_update(setup_to_run, self.log_message)
                            if ok_update:
                                try:
                                    modal.destroy()
                                    self.destroy()
                                except Exception:
                                    pass
                                os._exit(0)

                            is_downloading[0] = False
                            lbl_status.configure(text='❌ เปิดตัวติดตั้งผิดพลาด')
                            btn_action.configure(state='normal', text='🔄  ลองใหม่', fg_color=THEME['blue'], hover_color=THEME['blue_hover'])

                        modal.after(1000, do_shutdown_and_install)
                        return

                    time.sleep(1)
                    try:
                        apply_zip_update(target_file, self.log_message)
                        self.log_message('อัพเดตเสร็จสมบูรณ์!')
                        try:
                            modal.destroy()
                        except Exception:
                            pass
                        messagebox.showinfo('สำเร็จ', f'อัพเดตเป็นเวอร์ชัน {new_ver} สำเร็จ!')
                    except Exception as e:
                        self.log_message(f'อัพเดตผิดพลาด: {e}')
                else:
                    is_downloading[0] = False
                    try:
                        modal.after(0, lambda: [
                            lbl_status.configure(text='❌ ดาวน์โหลดอัพเดตผิดพลาด กรุณาลองใหม่!'),
                            btn_action.configure(state='normal', text='🔄  ลองใหม่', fg_color=THEME['blue'], hover_color=THEME['blue_hover'])
                        ])
                    except Exception:
                        pass

            threading.Thread(target=download_worker, daemon=True).start()

        btn_action.configure(command=start_download)
        modal.after(800, start_download)

    def on_closing(self):
        if self.server_mgr.is_running():
            ans = messagebox.askyesno('ออก', 'เซิร์ฟเวอร์ FO3 ยังทำงานอยู่ ต้องการปิดเซิร์ฟเวอร์และออกหรือไม่?')
            if not ans:
                return
            self.server_mgr.stop_server()
        self.destroy()


def check_single_instance():
    if sys.platform == 'win32':
        try:
            import ctypes
            mutex_name = 'Global\\FO3_Offline_Launcher_SingleInstance_Mutex'
            kernel32 = ctypes.windll.kernel32
            mutex = kernel32.CreateMutexW(None, False, mutex_name)
            last_error = kernel32.GetLastError()
            ERROR_ALREADY_EXISTS = 183
            if last_error == ERROR_ALREADY_EXISTS:
                return (False, mutex)
            return (True, mutex)
        except Exception:
            return (True, None)
    return (True, None)


def main():
    is_single, mutex = check_single_instance()
    if not is_single:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning('กำลังทำงาน', 'FO3 Launcher เปิดอยู่แล้ว!\nกรุณาตรวจสอบที่แถบงาน (Taskbar)')
        root.destroy()
        sys.exit(0)

    app = SimpleFO3Launcher()
    app.mainloop()


if __name__ == '__main__':
    main()
