from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_cancel_kb() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Bekor qilish")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# 1. Boshlang'ich (Salomlashish) oynasi - Inline tugmalar
def get_welcome_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="O'qituvchi sifatida kirish", callback_data="auth_teacher"
            )
        ],
        [
            InlineKeyboardButton(
                text="Talaba sifatida kirish", callback_data="auth_student"
            )
        ],
        [InlineKeyboardButton(text="Bot haqida", callback_data="about_bot")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# 2. Moderator Bosh Menyusi - Reply tugmalar
def get_teacher_menu(is_demo: bool = True) -> ReplyKeyboardMarkup:
    kb = [
        [
            KeyboardButton(text="Yangi test yaratish"),
            KeyboardButton(text="Mening testlarim"),
        ],
        [
            KeyboardButton(text="Mening obunam"),
            KeyboardButton(text="Tariflar va Imkoniyatlar"),
        ],
        [
            KeyboardButton(text="Qo'llanma"),
            KeyboardButton(text="Adminga murojaat")
        ],
        [KeyboardButton(text="Talaba rejimiga o'tish"), KeyboardButton(text="Tizimdan chiqish")]
    ]

    return ReplyKeyboardMarkup(
        keyboard=kb, resize_keyboard=True, one_time_keyboard=False
    )


# 3. Qo'llanma bo'limi - Inline tugmalar (Shablonlar va PDF yuklash)
def get_guide_download_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="PDF qo'llanma", callback_data="download_guide_pdf"
            )
        ],
        [
            InlineKeyboardButton(
                text="Savollar shabloni (Word)", callback_data="download_template_docx"
            )
        ],
        [
            InlineKeyboardButton(
                text="Talabalar shabloni (Excel)", callback_data="download_template_xlsx"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# 4. Student Bosh Menyusi - Reply tugmalar
def get_student_menu() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Tizimdan chiqish")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# 5. Student Imtihon topshirish boshlash - Inline tugma
def get_student_start_exam_kb(quiz_code: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="Imtihonni boshlash", callback_data=f"start_exam_{quiz_code}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# 6. Student Test yechish varianti - Inline tugmalar (A, B, C, D)
def get_student_answer_kb(question_index: int, options_count: int = 4) -> InlineKeyboardMarkup:
    # Variantlar: A, B, C, D (4 ta) yoki A, B, C (3 ta)
    row = []
    for idx in range(options_count):
        char = chr(65 + idx)  # 65 = 'A', 66 = 'B', ...
        row.append(
            InlineKeyboardButton(
                text=f"{char}", callback_data=f"ans_{question_index}_{idx}"
            )
        )

    buttons = [row]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# 7. Student test o'rtasida uzilib qolganda davom ettirish - Inline tugma
def get_student_resume_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="Davom ettirish", callback_data="resume_exam"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton

# 8. Super Admin Bosh Menyusi - Reply tugmalar
def get_admin_menu():
    kb = [
        [
            KeyboardButton(text="Statistika"),
            KeyboardButton(text="Foydalanuvchi menyusi"),
        ],
        [
            KeyboardButton(text="Buyruqlar ro'yxati")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
# 9. Super Admin Tarif Sozlamalari - Inline tugmalar
def get_admin_tariff_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="1 martalik limit narxi", callback_data="edit_onetime_price"
            )
        ],
        [
            InlineKeyboardButton(
                text="1 oylik obuna narxi", callback_data="edit_monthly_price"
            )
        ],
        [
            InlineKeyboardButton(
                text="Demo student limiti", callback_data="edit_demo_limit"
            )
        ],
        [
            InlineKeyboardButton(
                text="1 martalik student limiti", callback_data="edit_onetime_limit"
            )
        ],
        [
            InlineKeyboardButton(
                text="Monthly student limiti", callback_data="edit_monthly_limit"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
