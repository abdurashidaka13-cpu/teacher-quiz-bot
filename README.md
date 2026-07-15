# Moderatorlar va Studentlar uchun Telegram Test Bot

Ushbu loyiha o'qituvchilar (Moderatorlar) uchun sinxron boshlanadigan, savollari va javoblari chalkashadigan (shuffle), vaqt chekloviga ega kiberhimoyalangan testlar o'tkazish hamda natijalarini batafsil Excel baholash matritsasi va o'zlashtirilmagan savollar diagnostikasi bilan yuklab olish imkonini beruvchi Telegram bot tizimidir.

---

## 🚀 Texnologiyalar va Kutubxonalar
- **Dasturlash tili:** Python 3.10+
- **Bot kutubxonasi:** Aiogram 3.x (Asinxron)
- **Veb Server:** FastAPI + Uvicorn (Webhook va Health Check uchun)
- **Ma'lumotlar bazasi ORM:** SQLAlchemy Async + asyncpg
- **Ma'lumotlar bazasi:** PostgreSQL (Neon.tech yoki Supabase bulutli bepul bazalari tavsiya etiladi)
- **Fayllar bilan ishlash:** python-docx (Word variantlar parsingi) va pandas + openpyxl (Excel import/export)
- **Rasm siqish:** Pillow (rasmlarni WebP formatiga o'tkazib siqish)

---

## 📂 Loyiha Tuzilishi (Project Structure)
```
teacher-quiz-bot/
│
├── main.py                # FastAPI server va bot lifespani
├── config.py              # Loyiha sozlamalari (load_dotenv)
├── database.py            # PostgreSQL SQLAlchemy asinxron modellari
├── states.py              # FSM holatlari (Super Admin, Moderator, Student)
│
├── handlers/              # Bot buyruqlari va routerlari
│   ├── __init__.py
│   ├── common.py          # /start va salomlashish oynasi
│   ├── teacher.py         # Moderatorlik amallari, test yuklash
│   ├── student.py         # Student login va test yechish
│   └── admin.py           # Bosh admin boshqaruv paneli
│
├── keyboards/             # Tugmalar
│   ├── __init__.py
│   └── bot_keyboards.py   # Barcha inline va reply klaviaturalar
│
├── utils/                 # Yordamchi modullar
│   ├── __init__.py
│   ├── docx_parser.py     # Word jadval parsingi va Pillow WebP siqish
│   ├── excel_handler.py   # Student Excel baholash matritsasi generatori
│   └── throttling.py      # Tugmalarni tez-tez bosishga qarshi middleware
│
├── .gitignore             # Git ga yuklanmaydigan fayllar
├── requirements.txt       # Zarur kutubxonalar ro'yxati
├── env.example            # Sozlamalar shabloni
└── README.md              # Loyiha qo'llanmasi
```

---

## 🛠 Mahalliy Kompyuterda Ishga Tushirish (Local Setup)

Ushbu loyihani mahalliy kompyuteringizda (Lokal) ishlatish juda oson. Buning uchun quyidagi ketma-ketlikni bajaring:

### 1-Qadam: Loyiha papkasiga o'ting va Virtual Muhit yarating
Terminal/PowerShell-ni ochib loyiha papkasiga kiring:
```bash
# Virtual muhit yaratish
python -m venv venv

# Virtual muhitni faollashtirish (Windows)
.\venv\Scripts\activate

# Virtual muhitni faollashtirish (Linux/macOS)
source venv/bin/activate
```

### 2-Qadam: Zarur kutubxonalarni o'rnating
```bash
pip install -r requirements.txt
```

### 3-Qadam: Sozlamalarni (.env) kiriting
Loyiha papkasidagi `env.example` faylidan nusxa olib, yangi `.env` faylini yarating va quyidagi maxfiy sozlamalarni to'ldiring:
1. `BOT_TOKEN` - BotFather dan olingan Telegram token.
2. `DATABASE_URL` - Neon.tech yoki Supabase dan olingan asinxron PostgreSQL havolasi (Masalan: `postgresql+asyncpg://...` bilan boshlanishi kerak).
3. `ADMIN_IDS` - Sizning Telegram ID raqamingiz.
4. **DIQQAT (Lokal tekshirish):** Mahalliy kompyuterda webhook ishlamagani sababli `WEBHOOK_URL` qatorini **mutlaqo bo'sh qoldiring**. Shunda bot avtomatik ravishda **Polling (mahalliy)** rejimiga o'tadi va osongina ishga tushadi.

### 4-Qadam: Botni ishga tushiring
```bash
python main.py
```
*Bot muvaffaqiyatli ishga tushganda ma'lumotlar bazasi jadvallarini avtomatik yaratadi va `[BOT POLLING] Polling rejimida ish boshladi.` degan xabarni ko'rsatadi. Endi botingizga kirib sinab ko'rishingiz mumkin.*

---

## 🌐 Render.com Bulutli Serveriga Yuklash (Production Deployment)

Render.com bepul hostingiga yuklash uchun loyihani GitHub-ga qo'yish kerak:

### 1-Qadam: GitHub-ga yuklash (Git Commands)
Loyiha papkasida terminalda quyidagi buyruqlarni ishga tushiring:
```bash
# Git-ni loyihada faollashtirish
git init

# Barcha fayllarni saqlash (.env va venv avtomat ignore bo'ladi)
git add .
git commit -m "Initial commit of Quiz Bot"

# GitHub da yaratilgan yangi bo'sh repozitoriyaga ulash
git branch -M main
git remote add origin https://github.com/foydalanuvchi_nomi/teacher-quiz-bot.git
git push -u origin main
```

### 2-Qadam: Render.com da Web Service yaratish
1. Render.com ga kiring va **New +** -> **Web Service** tanlang.
2. O'zingizning GitHub loyihangizni bog'lang.
3. Sozlamalarni quyidagicha belgilang:
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. **Environment Variables** (Atrof-muhit sozlamalari) bo'limida quyidagilarni kiriting:
   - `BOT_TOKEN` = (Sizning bot tokeningiz)
   - `DATABASE_URL` = (PostgreSQL async URL manzil)
   - `ADMIN_IDS` = (Telegram ID laringiz)
   - `WEBHOOK_URL` = (Render.com sizga bergan to'liq havola, masalan: `https://my-quiz-bot.onrender.com`)
   - `WEBHOOK_SECRET` = (Istagan kuchli parolingiz, masalan: `SecretKey123!`)
5. **Create Web Service** tugmasini bosing. Render loyihangizni yig'ib (build) avtomatik webhook orqali ishga tushiradi!

---

## 🔒 Xavfsizlik va Kiberhimoya
- **Secret Token Authentication:** Botga faqat rasmiy Telegram serveridan kelgan webhook so'rovlari ruxsat etiladi, soxta so'rovlar filtrlanadi.
- **Throttling anti-spam:** Foydalanuvchilar tugmalarni spam (ketma-ket tez) bosa olishmaydi (botni qotirishdan himoya).
- **BYTEA rasm siqish:** O'qituvchilar yuklagan Word faylidagi rasmlar bazada 70% WebP shaklida siqib saqlanadi, bu Neon.tech bepul bazasi to'lib ketishini oldini oladi.
- **Avtomatik tozalash (Cleanup):** No-faol demo va muddati tugagan obunachilar ma'lumotlari har kuni 1 marta avtomat o'chiriladi.
