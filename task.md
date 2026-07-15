# Loyiha Vazifalari Ro'yxati (Loyiha Checklist)

Ushbu hujjat Telegram Quiz Bot loyihasini yaratish jarayonini boshqarish va nazorat qilish uchun TODO (vazifalar) ro'yxatidir.

## 1. Poydevor va Konfiguratsiya
- [x] `requirements.txt` - Kutubxonalar ro'yxatini yaratish
- [x] `.gitignore` - GitHub-ga yuklanmaydigan fayllar qoidasi
- [x] `config.py` - Sozlamalar va atrof-muhit o'zgaruvchilari boshqaruvi
- [x] `.env` - Maxfiy sozlamalar shablon fayli

## 2. Ma'lumotlar Bazasi Modeli (`database.py`)
- [x] PostgreSQL SQLAlchemy asinxron modellarini yaratish
- [x] `system_settings` - Tizim sozlamalari va tarif limitlari jadvali
- [x] `users` va `subscriptions` - Moderatorlar va obunalar jadvali
- [x] `quizzes` va `questions` - Testlar va savollar (binary rasmlari bilan) jadvali
- [x] `students` - Studentlar ro'yxati va seanslari jadvali
- [x] `student_attempts` va `student_answers` - Imtihon natijalari va javoblar jadvali
- [x] Asinxron ulanish puli (connection pool) va jadvallarni yaratish logikasi

## 3. Fayllarni Parsing qilish va Validatsiya (`utils/`)
- [x] `utils/docx_parser.py` - Word jadvalini o'qish, rasmlarni XML dan ajratish, Pillow WebP (70% sifat, 800px) siqish va xatoliklarni tekshirish (6 ustunlik qat'iy tekshiruv)
- [x] `utils/excel_handler.py` - Studentlar ro'yxatini validatsiya qilish, student baholash matritsasi (Sheet 1: Summary, Sheet 2: Matritsa, ustun/qator yig'indilari, o'rtacha foiz va 3 ta eng qiyin savollar tahlili) Excel hisobotini yaratish

## 4. Bot Arxitekturasi va Middleware
- [x] `states.py` - FSM holatlari (Super Admin, Moderator, Student va ro'yxatdan o'tish holatlari)
- [x] `main.py` - FastAPI ilovasi, Uvicorn, Webhook sozlamalari, secret token tekshiruvi va aiogram dispatcher sozlamalari
- [x] Throttling Middleware - Bot ichida tugmalarni spam qilishga qarshi cheklov qatlami

## 5. Telegram Handlers (`handlers/`)
- [x] `handlers/common.py` - Boshlang'ich `/start` salomlashish, mehmonga rollar taklif qilish (login / moderatorlik)
- [x] `handlers/teacher.py` - Moderator ro'yxatdan o'tishi, test sozlamalari, Word va Excel yuklash, kutish zali jonli nazorati, imtihon davomida jonli nazorat (tugatganlar/yechayotganlar progressi), natijalar yuklash, murojaat yuborish
- [x] `handlers/admin.py` - Super Admin boshqaruv paneli, jonli va umumiy statistika, foydalanuvchilar obunasini tahrirlash, tarif sozlamalarini (narx va limitlar) dinamik o'zgartirish, global Anti-Flood xabarnoma tarqatish, kelgan murojaatlarga javob yozish
- [x] `handlers/student.py` - Student login-parol tizimi, kutish seansi, testni boshlash, savollarni double-shuffle (tartib + variantlar) shaklida bitta-bitta yechish, server-side vaqt tekshiruvi, auto-logout seans tozalash

## 6. Avtomatik Fon Rejimi (Background Cleanup)
- [x] FastAPI startup hodisasida har kuni avtomatik ishlovchi demo va expired hisoblar bazasini tozalash (30 kunlik muddat) funksiyasi

## 7. Qo'llanmalar va Yo'riqnomalar
- [x] `README.md` - Loyihani yangi kompyuterda yoki uydagi kompyuterda ishga tushirish bo'yicha mukammal qo'llanma
