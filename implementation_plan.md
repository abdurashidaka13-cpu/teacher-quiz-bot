# Moderatorlar va Studentlar uchun Telegram Test Bot (Fayllarni Tekshirish va Validatsiya)

Ushbu loyiha **Moderatorlar**ga pullik paketlarni simulyatsiya qilish orqali test yaratish, **Studentlar** ro'yxatini Excel fayli, test savollarini esa **har bir variant uchun alohida Word (docx) fayllari** orqali yuklash, test seansiga **bitta yoki bir nechta variantlarni biriktirish (Tanlov tizimi)**, Studentlar login-parol bilan kirib bo'lgach **Moderatorning joriy kutish zalidagi tayyor va tayyor bo'lmagan Studentlar hisobotini jonli ko'rishi**, yagona tugma orqali imtihonni sinxron boshlash, **imtihon davomida kimlar topshirganini jonli kuzatish**, savollar va ularning **javob variantlarini (A, B, C, D) chalkashtirib (shuffle)** Studentlarga ko'rsatish, vaqt cheklovi bilan imtihon olish va natijalarni Excel hisobotida taqdim etish imkonini beradi.

Shuningdek, **Super Admin (Siz)** boshqaruv paneli, qayta aloqa va **fayllarni oldindan tekshirish va validatsiya qilish tizimi** mavjud bo'ladi.

---

## 1. Fayllarni Oldindan Validatsiya Qilish Tizimi (File Pre-Validation)

Moderator tomonidan yuklanadigan barcha fayllar ma'lumotlar bazasiga yozilishidan oldin **qat'iy strukturaviy tekshiruvdan** o'tkaziladi. Agar xatolik topilsa, tranzaksiya bekor qilinadi va Moderatorga aniq qayerda xato qilgani ko'rsatilib, shablonga muvofiq to'ldirish so'raladi.

### 1.1. Studentlar Ro'yxati (Excel - .xlsx) Validatsiyasi:
Bot Excel faylini qabul qilganda quyidagilarni tekshiradi:
1.  **Format:** Fayl kengaytmasi `.xlsx` ekanligi.
2.  **Ustunlar nomi:** Birinchi ustun nomi qat'iy **`Ism Familiya`** deb yozilganligi (probellar va katta-kichik harflar tekshiriladi).
3.  **Tarkib:** Jadvalda kamida 1 ta student ismi yozilganligi.
- **Xato bo'lsa:** Bot bazaga hech narsa yozmaydi va rad etadi:
  > ⚠️ **Xatolik: Yuklangan Excel fayli yaroqsiz!**  
  > - Birinchi ustun nomi "Ism Familiya" bo'lishi shart.  
  > - Iltimos, shablon bo'yicha to'ldirib, qayta yuboring.  
  > [📥 Excel Shablonini Yuklash]

---

### 1.2. Savollar Hujjati (Word - .docx) Validatsiyasi:
Bot Word faylini qabul qilganda quyidagilarni qat'iy tekshiradi:
1.  **Struktura:** Fayl ichida jadval (table) borligi va jadval ustunlari soni **aynan 6 ta** ekanligi.
2.  **Qatorlar bo'yicha tekshiruv (Row Validation):**
    - 1-ustun (T/r) son bo'lishi kerak.
    - 2-ustun (Savol) bo'sh bo'lmasligi kerak (matn yoki rasm bo'lishi shart).
    - 3-ustun (To'g'ri javob) va 4, 5, 6-ustunlar (Distraktorlar) bo'sh bo'lmasligi kerak.
- **Xato bo'lsa:** Bot tranzaksiyani orqaga qaytaradi (rollback) va xatoliklar hisobotini yuboradi:
  > ⚠️ **Xatolik: Word faylida xatolar aniqlandi!**  
  > - `12-savol:` Variant 2 katagi bo'sh qolgan.  
  > - `25-savol:` Variant 3 katagi bo'sh qolgan.  
  > *Iltimos, savollarni shablonga muvofiq to'liq (1 ta to'g'ri va 3 ta noto'g'ri javob bilan) to'ldirib, qayta yuboring.*  
  > [📥 Word Shablonini Yuklash]

---

## 2. Loyiha Tuzilishi va Fayllari

### [NEW] [teacher-quiz-bot](file:///C:/Users/K.M.Axmadjanovich/.gemini/antigravity/scratch/teacher-quiz-bot)
- Word va Excel fayllarini oldindan tekshiruvchi validator modullari (`utils/docx_parser.py` va `utils/excel_handler.py`).
