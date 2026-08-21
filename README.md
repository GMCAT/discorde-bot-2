# Discord Contacts Bot

Discord bot ภาษาไทยสำหรับค้นหาและจัดการข้อมูลผู้ติดต่อบน PostgreSQL โดยมีเฉพาะ
`ContactService` และ `AdminService` ไม่มีระบบข่าวหรือ AI

## ความสามารถ

- `/contact` ค้นจากชื่อ เบอร์ อีเมล ตำแหน่ง หรือหน่วยงาน
- `/emergency` แสดงผู้ติดต่อฉุกเฉิน
- `/add-contact` เพิ่มข้อมูล (เฉพาะแอดมิน)
- `/database-status` ตรวจฐานข้อมูล (เฉพาะแอดมิน)
- `/all-contacts` แสดงข้อมูลทั้งหมด (เฉพาะแอดมิน)
- รองรับคำสั่งข้อความภาษาไทยเหมือน LINE bot
- แบ่งผลลัพธ์ที่ยาวเกิน 2,000 ตัวอักษรอัตโนมัติ

## ติดตั้ง

ต้องใช้ Python 3.10+ และ PostgreSQL/Neon

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

คัดลอก `.env.example` เป็น `.env` แล้วกรอกค่าจริง จากนั้นสร้างตารางด้วย `schema.sql`
ผ่าน Neon SQL Editor หรือ `psql`:

```bash
psql "$DATABASE_URL" -f schema.sql
python -m bot.main
```

ต้องเปิด **Message Content Intent** ใน Discord Developer Portal หากต้องการใช้คำสั่งข้อความ
และเชิญบอทด้วย scopes `bot`, `applications.commands` พร้อมสิทธิ์ View Channels,
Send Messages และ Read Message History

`DISCORD_ADMIN_USER_IDS` ต้องเป็น Discord user ID คั่นด้วย comma หากเว้นว่าง
คำสั่งแอดมินจะถูกปฏิเสธทุกคน

## คำสั่งข้อความ

ใน DM ใช้ `ติดต่อ นายเอ`, `ติดต่อฉุกเฉิน` หรือฟอร์ม `เพิ่มติดต่อ` ได้โดยตรง
ใน server ต้อง mention บอทหรือใช้ prefix เช่น:

```text
!ติดต่อ ฝ่ายไอที
```

```text
!เพิ่มติดต่อ
ชื่อ: นายเอ
หน่วยงาน: ฝ่ายไอที
เบอร์: 0812345678
ประเภท: IT
บทบาท: หลัก
24ชม: ไม่
```

## ทดสอบ

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## อัปขึ้น GitHub

รันคำสั่งจากภายในโฟลเดอร์นี้:

```bash
git init
git add .
git commit -m "Initial Discord contacts bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/discord-contacts-bot.git
git push -u origin main
```

อย่า commit ไฟล์ `.env` หรือ token จริง โดย `.gitignore` ป้องกัน `.env` ไว้แล้ว

