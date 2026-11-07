# FO3TH OFFLINE — Launcher (ภาษาไทย)

Launcher สำหรับเซิร์ฟเวอร์ออฟไลน์ FIFA Online 3 พร้อมอินเทอร์เฟซภาษาไทยครบทุกส่วน

> ตัว launcher อ้างอิงจากโปรเจกต์ FO3 Offline ของ Ý Trịnh (fo3offline.asia) มาพัฒนาต่อ
> ขอบคุณผู้พัฒนาต้นฉบับ — ช่องทางสนับสนุนต้นฉบับคงอยู่ในหน้า "สนับสนุนผู้พัฒนา" ของ launcher

## ฟีเจอร์

- เปิดเซิร์ฟเวอร์ออฟไลน์ + เข้าเกมในปุ่มเดียว
- หาโฟลเดอร์เกมอัตโนมัติ (สแกนทุกไดรฟ์)
- สำรอง/กู้คืนเซฟ, กู้ฉุกเฉินข้อมูลผู้จัดการทีม, รีเซ็ตฐานข้อมูล
- ผู้ดูแลเว็บ (Web Admin) ที่พอร์ต 8088
- **เช็คอัพเดตอัตโนมัติทุกครั้งที่เปิดโปรแกรม** จาก GitHub Releases ของ repo นี้

## สำหรับผู้เล่น

ดาวน์โหลด `FO3TH_Launcher.exe` ล่าสุดจาก [Releases](https://github.com/ArtTheerawat/FO3TH-OFFLINE/releases)
วางไว้ในโฟลเดอร์เซิร์ฟเวอร์ (ข้าง ๆ โฟลเดอร์ `Server`) แล้วดับเบิลคลิก

## สำหรับเจ้าของเซิร์ฟ (การพัฒนาต่อ)

โครงสร้าง:

```
launcher/
├── FO3_Launcher.py          ← หน้าจอหลัก (UI ภาษาไทย)
├── launcher_core/
│   ├── config.py            ← ค่าตั้งต้น: เวอร์ชัน, repo อัพเดต
│   ├── updater.py           ← ระบบเช็ค/ดาวน์โหลดอัพเดต
│   ├── server_manager.py    ← เริ่ม/หยุดเซิร์ฟเวอร์
│   ├── game_manager.py      ← หาเกม/เปิดเกม
│   ├── backup_manager.py    ← สำรอง/กู้คืนเซฟ
│   └── hosts_manager.py     ← ตั้งค่า hosts สำหรับโหมดออฟไลน์
└── assets/                  ← โลโก้ ไอคอน
```

- แก้โค้ดเสร็จ → ดับเบิลคลิก `build_launcher.bat` → ได้ EXE ใหม่
- วิธีปล่อยอัพเดตให้ผู้เล่น: ดู `docs/วิธีอัพเดต.md` (สั้น ๆ: ขยับเลข version → build → อัพ Releases ด้วย tag `vเลขใหม่`)

## ต้องติดตั้งอะไรก่อน build

- Python 3.15 (Windows x64)
- `python -m pip install customtkinter pillow requests pyinstaller`
