import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func

from config import ADMIN_IDS
from database import async_session, User, Quiz, Student, StudentAttempt, SystemSettings, Subscription
from keyboards.bot_keyboards import get_admin_menu, get_admin_tariff_kb, get_teacher_menu
from states import AdminStates

router = Router(name="admin")

# Faqat ADMIN_IDS ro'yxatidagi adminlargagina ruxsat berish (swallowing oldini olish)
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


# FSM blokirovkasini (deadlock) oldini oluvchi middleware
@router.message.middleware()
async def admin_fsm_cancel_middleware(handler, event: Message, data: dict):
    state: FSMContext = data.get("state")
    current_state = await state.get_state() if state else None
    if current_state is not None and event.text in [
        "Statistika",
        "Tariflar",
        "Xabar yuborish",
        "Murojaatlar",
        "Obuna berish",
        "Foydalanuvchi menyusi",
        "Buyruqlar ro'yxati",
        "/start"
    ]:
        await state.clear()
        from handlers.common import cmd_start
        await cmd_start(event, state)
        return
    return await handler(event, data)


# ==========================================
# 1. BUYRUQLAR RO'YXATI
# ==========================================
@router.message(F.text == "Buyruqlar ro'yxati")
@router.message(Command("admin", "commands"))
async def show_admin_commands(message: Message):
    """Admin uchun barcha mavjud buyruqlar va imkoniyatlar ro'yxatini chiqarish"""
    if message.from_user.id not in ADMIN_IDS:
        return

    text = (
        "🛠 **Boshqaruv Buyruqlari Ro'yxati:**\n\n"
        "🔸 `/mod` - Maxsus foydalanuvchini moderator qilish. To'g'ridan-to'g'ri huquq berish uchun `/mod [ID yoki @username] [limitlar] [o'quvchi limiti] [kun]` shaklida yoki faqat `/mod` qilib interaktiv menyuni ochishingiz mumkin.\n"
        "🔸 `/mod1` - Standart 1 martalik limitni tezkor berish (`/mod1 @username`).\n"
        "🔸 `/mod2` - Standart 30 kunlik Premium obunani tezkor berish (`/mod2 123456789`).\n"
        "🔸 `/stats` - Tizimdagi jami moderatorlar, talabalar va testlar bo'yicha jonli statistikani chiqaradi.\n"
        "🔸 `/users` - Barcha foydalanuvchilarning to'liq ro'yxati, ruxsatlari, obunalari va statistikasini Excel faylda yuklab beradi.\n"
        "🔸 `/prices` - Obuna narxlari va global talabalar limitini (demo/premium) tahrirlash menyusini ochadi.\n"
        "🔸 `/broadcast` - Barcha foydalanuvchilar yoki faqat moderatorlarga ommaviy xabar tarqatishni boshlaydi.\n"
        "🔸 `/teacher` - Admin panelni yopib, test yaratish va o'quvchi qo'shish kabi oddiy moderator menyusiga o'tadi.\n"
        "🔸 `/admin` - Ayni shu buyruqlar yo'riqnomasini qayta ochadi.\n\n"
        "_Ushbu ro'yxat kelajakda ehtiyojga qarab yangi buyruqlar bilan boyitib boriladi._"
    )
    await message.answer(text, parse_mode="Markdown")

# ==========================================
# 2. TIZIM STATISTIKASI
# ==========================================
@router.message(F.text == "Statistika")
@router.message(Command("stats", "statistika"))
async def show_system_stats(message: Message):
    """Botdagi barcha jadvallar bo'yicha jonli statistikani ko'rsatadi"""
    if message.from_user.id not in ADMIN_IDS:
        return

    async with async_session() as session:
        # Moderatorlar soni
        mod_res = await session.execute(
            select(func.count(User.id)).where(User.role == "moderator")
        )
        mod_count = mod_res.scalar()

        # Jami testlar soni
        quiz_res = await session.execute(select(func.count(Quiz.id)))
        quiz_count = quiz_res.scalar()

        # Faol imtihonlar
        active_res = await session.execute(
            select(func.count(Quiz.id)).where(Quiz.status == "active")
        )
        active_count = active_res.scalar()

        # Jami studentlar
        stud_res = await session.execute(select(func.count(Student.id)))
        stud_count = stud_res.scalar()

        # Jami topshirilgan urinishlar
        attempt_res = await session.execute(
            select(func.count(StudentAttempt.id)).where(StudentAttempt.completed_at.isnot(None))
        )
        attempt_count = attempt_res.scalar()

    stats_text = (
        f"📊 **TIZIM JONLI STATISTIKASI:**\n\n"
        f"👨‍🏫 **Moderatorlar (O'qituvchilar):** {mod_count} ta\n"
        f"👥 **Studentlar (O'quvchilar):** {stud_count} ta\n\n"
        f"📚 **Jami yaratilgan testlar:** {quiz_count} ta\n"
        f"🚀 **Ayni paytda faol testlar:** {active_count} ta\n"
        f"✅ **Tugatilgan urinishlar:** {attempt_count} ta\n"
    )
    await message.answer(stats_text, reply_markup=get_admin_menu(), parse_mode="Markdown")


# ==========================================
# 3. TARIF SOZLAMALARI (DINAMIK)
# ==========================================
@router.message(F.text == "Tariflar")
@router.message(Command("prices", "tariflar"))
async def show_tariffs_menu(message: Message):
    """Tarif narxlari va o'quvchilar soni limitlarini ko'rsatish/tahrirlash"""
    if message.from_user.id not in ADMIN_IDS:
        return

    async with async_session() as session:
        settings_res = await session.execute(select(SystemSettings))
        settings = settings_res.scalar()

    tariff_text = (
        f"💰 **JORIY TARIF VA LIMIT SOZLAMALARI:**\n\n"
        f"🎟 **1 martalik limit narxi:** {settings.onetime_price:,} so'm\n"
        f"💳 **1 oylik obuna narxi:** {settings.monthly_price:,} so'm\n\n"
        f"📌 **Student limits (Maksimal o'quvchi soni):**\n"
        f"- Bepul Demo tarifi: {settings.demo_max_students} ta\n"
        f"- 1 martalik limitda: {settings.onetime_max_students} ta\n"
        f"- 1 oylik Premiumda: {settings.monthly_max_students} ta\n\n"
        f"_Qiymatlarni o'zgartirish uchun ostidagi tugmalardan birini tanlang:_"
    )
    await message.answer(tariff_text, reply_markup=get_admin_tariff_kb(), parse_mode="Markdown")


# --- EDIT HANDLERS FOR SETTINGS ---
@router.callback_query(F.data == "edit_onetime_price")
async def edit_ot_price(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_onetime_price)
    await callback.message.answer("🎟 Yangi 1 martalik limit narxini kiriting (faqat son, so'mda):")
    await callback.answer()


@router.message(AdminStates.waiting_for_onetime_price)
async def process_ot_price(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val.isdigit() or int(val) < 0:
        await message.answer("Iltimos, yaroqli son kiriting:")
        return

    async with async_session() as session:
        settings = (await session.execute(select(SystemSettings))).scalar()
        settings.onetime_price = int(val)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ 1 martalik limit narxi {int(val):,} so'mga o'zgartirildi.")
    await show_tariffs_menu(message)


@router.callback_query(F.data == "edit_monthly_price")
async def edit_mon_price(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_monthly_price)
    await callback.message.answer("💳 Yangi 1 oylik Premium narxini kiriting (faqat son, so'mda):")
    await callback.answer()


@router.message(AdminStates.waiting_for_monthly_price)
async def process_mon_price(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val.isdigit() or int(val) < 0:
        await message.answer("Iltimos, yaroqli son kiriting:")
        return

    async with async_session() as session:
        settings = (await session.execute(select(SystemSettings))).scalar()
        settings.monthly_price = int(val)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ 1 oylik Premium narxi {int(val):,} so'mga o'zgartirildi.")
    await show_tariffs_menu(message)


@router.callback_query(F.data == "edit_demo_limit")
async def edit_dm_limit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_demo_limit)
    await callback.message.answer("📌 Yangi Demo student limitini kiriting (Masalan: 5):")
    await callback.answer()


@router.message(AdminStates.waiting_for_demo_limit)
async def process_dm_limit(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val.isdigit() or int(val) <= 0:
        await message.answer("Iltimos, noldan katta butun son kiriting:")
        return

    async with async_session() as session:
        settings = (await session.execute(select(SystemSettings))).scalar()
        settings.demo_max_students = int(val)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Demo student limiti {val} taga o'zgartirildi.")
    await show_tariffs_menu(message)


@router.callback_query(F.data == "edit_onetime_limit")
async def edit_ot_limit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_onetime_limit)
    await callback.message.answer("📌 Yangi 1 martalik student limitini kiriting (Masalan: 30):")
    await callback.answer()


@router.message(AdminStates.waiting_for_onetime_limit)
async def process_ot_limit(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val.isdigit() or int(val) <= 0:
        await message.answer("Iltimos, noldan katta butun son kiriting:")
        return

    async with async_session() as session:
        settings = (await session.execute(select(SystemSettings))).scalar()
        settings.onetime_max_students = int(val)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ 1 martalik student limiti {val} taga o'zgartirildi.")
    await show_tariffs_menu(message)


@router.callback_query(F.data == "edit_monthly_limit")
async def edit_mon_limit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_monthly_limit)
    await callback.message.answer("📌 Yangi Premium student limitini kiriting (Masalan: 100):")
    await callback.answer()


@router.message(AdminStates.waiting_for_monthly_limit)
async def process_mon_limit(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val.isdigit() or int(val) <= 0:
        await message.answer("Iltimos, noldan katta butun son kiriting:")
        return

    async with async_session() as session:
        settings = (await session.execute(select(SystemSettings))).scalar()
        settings.monthly_max_students = int(val)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Premium student limiti {val} taga o'zgartirildi.")
    await show_tariffs_menu(message)


# ==========================================
# 4. GLOBAL E'LON TARQATISH (ANTI-FLOOD)
# ==========================================
@router.message(F.text == "Xabar yuborish")
@router.message(Command("broadcast", "xabar"))
async def cmd_broadcast_start(message: Message, state: FSMContext):
    """E'lon matnini so'rash"""
    if message.from_user.id not in ADMIN_IDS:
        return

    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await message.answer(
        "📢 **Global E'lon tarqatish bo'limi:**\n\nYubormoqchi bo'lgan xabaringiz matnini kiriting (rasmli bo'lishi ham mumkin):"
    )


@router.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    """E'lon kimlarga yuborilishini so'rash"""
    # Xabar matnini va media fayllarini saqlash
    await state.update_data(
        broadcast_msg_text=message.text or message.caption,
        broadcast_photo=message.photo[-1].file_id if message.photo else None,
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Faqat Moderatorlarga", callback_data="target_moderators"
                )
            ],
            [InlineKeyboardButton(text="Barcha Foydalanuvchilarga", callback_data="target_all")],
        ]
    )

    await message.answer("Xabar kimlarga tarqatilsin?", reply_markup=kb)


@router.callback_query(AdminStates.waiting_for_broadcast_text, F.data.startswith("target_"))
async def cb_broadcast_execute(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Global e'lonni asinxron va anti-flood navbat orqali tarqatish"""
    target = callback.data.split("_")[1]
    data = await state.get_data()
    text = data.get("broadcast_msg_text")
    photo_id = data.get("broadcast_photo")

    await state.clear()
    await callback.message.edit_text("🔄 Xabar tarqatilmoqda. Iltimos, kuting...")

    # Yuboriladigan foydalanuvchilar ID sini olish
    ids = []
    async with async_session() as session:
        if target == "moderators":
            stmt = select(User.id).where(User.role == "moderator")
            res = await session.execute(stmt)
            ids = res.scalars().all()
        else:
            # Barcha foydalanuvchilar (moderatorlar)
            stmt1 = select(User.id)
            res1 = await session.execute(stmt1)
            ids1 = res1.scalars().all()

            # Faol studentlar
            stmt2 = select(Student.telegram_id).where(Student.telegram_id.isnot(None))
            res2 = await session.execute(stmt2)
            ids2 = res2.scalars().all()

            ids = list(set(ids1 + ids2))

    success = 0
    failed = 0

    # Anti-flood delay: har bir xabardan so'ng 0.05 soniya asinxron to'xtash
    for u_id in ids:
        try:
            if photo_id:
                await bot.send_photo(u_id, photo_id, caption=text)
            else:
                await bot.send_message(u_id, text)
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await callback.message.answer(
        f"📢 **E'lon tarqatish yakunlandi!**\n\n"
        f"✅ Muvaffaqiyatli yetkazildi: {success} ta\n"
        f"❌ Xatolik tufayli bormadi: {failed} ta",
        reply_markup=get_admin_menu(),
    )
    await callback.answer()


# ==========================================
# 5. QAYTA ALOQA TICKETLARIGA JAVOB YOZISH
# ==========================================
@router.callback_query(F.data.startswith("reply_ticket_"))
async def cb_reply_ticket_start(callback: CallbackQuery, state: FSMContext):
    """Admin chiptaga javob yozishni boshlaydi"""
    target_user_id = int(callback.data.split("_")[2])
    await state.set_state(AdminStates.waiting_for_ticket_reply)
    await state.update_data(target_ticket_user_id=target_user_id)

    await callback.message.answer(
        f"✍️ `{target_user_id}` ID li foydalanuvchining yordam so'roviga javob yozing:"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_ticket_reply)
async def process_ticket_reply(message: Message, state: FSMContext, bot: Bot):
    """Javobni moderatorga yo'llash"""
    reply_text = message.text.strip()
    if not reply_text:
        await message.answer("Javob matni bo'sh bo'lishi mumkin emas.")
        return

    data = await state.get_data()
    target_id = data["target_ticket_user_id"]

    await state.clear()

    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Adminga xabar yuborish", callback_data="contact_admin")]
        ])
        await bot.send_message(
            target_id,
            f"✉️ **Bosh admin sizning murojaatingizga javob yubordi:**\n\n"
            f"{reply_text}",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await message.answer("✅ Javobingiz foydalanuvchiga yuborildi.")
    except Exception as e:
        await message.answer(f"❌ Javobni yuborib bo'lmadi (Foydalanuvchi botni bloklagan bo'lishi mumkin): {e}")


# ==========================================
# 6. FOYDALANUVCHI MENYUSIGA O'TISH
# ==========================================
@router.message(F.text == "Foydalanuvchi menyusi")
@router.message(Command("teacher"))
async def switch_to_user_menu(message: Message, state: FSMContext):
    """Adminning oddiy moderator menyusiga o'tishi (test yechish yoki test yaratish uchun)"""
    if message.from_user.id not in ADMIN_IDS:
        return

    await message.answer(
        "Moderator menyusiga o'tdingiz. Bu yerdan testlarni boshqarishingiz mumkin.",
        reply_markup=get_teacher_menu(is_demo=False),
    )


@router.message(F.text == "Murojaatlar")
async def show_support_tickets_queue(message: Message):
    """Murojaatlar navbati haqida ma'lumot (Telegram PM orqali ishlashi haqida)"""
    if message.from_user.id not in ADMIN_IDS:
        return

    text = (
        "📥 **Murojaatlar Navbati boshqaruvi:**\n\n"
        "Moderatorlar (o'qituvchilar) tomonidan yuborilgan barcha murojaatlar sizga (Bosh Adminga) "
        "to'g'ridan-to'g'ri Telegram shaxsiy xabari ko'rinishida yuboriladi.\n\n"
        "Javob berish uchun o'sha kelgan xabarning ostidagi **Javob yozish ✍️** tugmasini bosishingiz kifoya.\n\n"
        "✅ Hozirda faol/javobsiz qolgan navbatdagi murojaatlar mavjud emas."
    )
    await message.answer(text, reply_markup=get_admin_menu(), parse_mode="Markdown")


# ==========================================
# 7. OBUNA BERISH (MANUAL SUBSCRIPTION)
# ==========================================
@router.message(F.text == "Obuna berish")
async def cmd_give_sub_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_user_id)
    await message.answer("Foydalanuvchining (Moderatorning) Telegram ID raqamini kiriting:")


@router.message(AdminStates.waiting_for_user_id)
async def process_give_sub_user_id(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val.isdigit():
        await message.answer("Iltimos, yaroqli ID (son) kiriting yoki /start bosing:")
        return

    target_id = int(val)
    async with async_session() as session:
        user = await session.execute(select(User).where(User.id == target_id))
        user = user.scalar_one_or_none()
        if not user or user.role != "moderator":
            await message.answer("Bunday ID ga ega moderator topilmadi. Qaytadan kiriting:")
            return

    await state.update_data(target_id=target_id)
    await state.set_state(AdminStates.waiting_for_sub_type)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 Oylik Premium", callback_data="give_sub_monthly")],
        [InlineKeyboardButton(text="5 ta Bir martalik limit", callback_data="give_sub_onetime")]
    ])
    await message.answer(f"Moderator: {user.full_name}\nQanday turdagi obuna bermoqchisiz?", reply_markup=kb)


@router.callback_query(AdminStates.waiting_for_sub_type, F.data.startswith("give_sub_"))
async def process_give_sub_type(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_id = data.get("target_id")
    sub_type = callback.data.split("_")[2]

    async with async_session() as session:
        if sub_type == "monthly":
            import datetime
            from config import local_now
            # Remove existing monthly if any, or just add new
            await session.execute(delete(Subscription).where(Subscription.user_id == target_id, Subscription.type == "monthly"))
            new_sub = Subscription(
                user_id=target_id,
                type="monthly",
                expires_at=local_now() + datetime.timedelta(days=30)
            )
            session.add(new_sub)
            msg_text = "🎉 Sizga Admindan 1 oylik Premium obuna sovg'a qilindi!"
            ans_text = "✅ 1 oylik Premium muvaffaqiyatli berildi."
        else:
            new_sub = Subscription(
                user_id=target_id,
                type="onetime",
                credits=5
            )
            session.add(new_sub)
            msg_text = "🎉 Sizga Admindan 5 ta bir martalik test yaratish limiti sovg'a qilindi!"
            ans_text = "✅ 5 ta bir martalik limit muvaffaqiyatli berildi."

        await session.commit()

    await callback.message.edit_text(ans_text)
    await state.clear()
    
    try:
        await bot.send_message(target_id, msg_text)
    except Exception:
        pass
import datetime
from sqlalchemy import delete
from database import local_now

# ... This will be merged into admin.py

async def resolve_user_from_ident(session, ident: str):
    ident = ident.strip()
    if ident.startswith("@"):
        username = ident[1:]
        stmt = select(User).where(User.username == username)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()
    elif ident.isdigit():
        return await session.get(User, int(ident))
    return None

@router.message(Command("mod", "moderator"))
async def cmd_mod_advanced(message: Message, state: FSMContext, bot: Bot):
    """
    Formati: /mod [ID yoki @username] [urinishlar soni] [o'quvchi soni] [muddat]
    yoki /mod (interaktiv menyu)
    """
    args = message.text.split()
    
    if len(args) == 1:
        await state.set_state(AdminStates.waiting_for_mod_id)
        await message.answer(
            "👤 **Boshqariladigan foydalanuvchining Telegram ID yoki @username ini kiriting:**\n\n"
            "_Maslahat: Siz to'g'ridan-to'g'ri `/mod @username 1 50 30` shaklida ham yozishingiz mumkin._",
            parse_mode="Markdown"
        )
        return

    ident = args[1]
    
    async with async_session() as session:
        user = await resolve_user_from_ident(session, ident)
        if not user:
            await message.answer(f"❌ `{ident}` ga ega foydalanuvchi bazada topilmadi.", parse_mode="Markdown")
            return
            
        if len(args) == 2:
            await process_mod_target(message, user.id, state)
            return

        if len(args) >= 5:
            try:
                tickets = int(args[2])
                max_students = int(args[3])
                days = int(args[4])
            except ValueError:
                await message.answer("❌ Parametrlar noto'g'ri. Raqam bo'lishi kerak:\n`/mod @username [limitlar] [max_students] [days]`", parse_mode="Markdown")
                return

            user.role = "moderator"
            
            added = False
            if days > 0:
                expires_at = local_now() + datetime.timedelta(days=days)
                new_sub = Subscription(
                    user_id=user.id,
                    type="monthly",
                    max_students_limit=max_students,
                    expires_at=expires_at
                )
                session.add(new_sub)
                added = True
            
            if tickets > 0:
                new_sub_t = Subscription(
                    user_id=user.id,
                    type="onetime",
                    max_students_limit=max_students,
                    credits=tickets
                )
                session.add(new_sub_t)
                added = True
                
            if added:
                await session.commit()
                await message.answer(f"✅ Foydalanuvchiga muvaffaqiyatli huquqlar berildi!\n\nUser: {user.full_name}\nLimitlar: {tickets}\nPremium: {days} kun\nLimit: {max_students} o'quvchi.")
                try:
                    await bot.send_message(user.id, f"🎉 Admindan maxsus ruxsatlar berildi!\n\n🎟 Limitlar: {tickets} ta\n🌟 Premium: {days} kun\n👥 O'quvchi limiti: {max_students} ta")
                except:
                    pass
            else:
                await message.answer("❌ Hech qanday ruxsat berilmadi (kun va limitlar 0 bo'lsa).")

@router.message(Command("mod1"))
async def cmd_mod1(message: Message, bot: Bot):
    """/mod1 [ID yoki @username] - standart bir martalik limit beradi."""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Formati: `/mod1 [ID yoki @username]`", parse_mode="Markdown")
        return
        
    ident = args[1]
    async with async_session() as session:
        user = await resolve_user_from_ident(session, ident)
        if not user:
            await message.answer(f"❌ `{ident}` topilmadi.", parse_mode="Markdown")
            return
            
        settings = (await session.execute(select(SystemSettings))).scalar()
        
        user.role = "moderator"
        new_sub = Subscription(
            user_id=user.id,
            type="onetime",
            max_students_limit=settings.onetime_max_students,
            credits=1
        )
        session.add(new_sub)
        await session.commit()
        
        await message.answer(f"✅ {user.full_name} ga 1 ta limit berildi (Limit: {settings.onetime_max_students}).")
        try:
            await bot.send_message(user.id, f"🎉 Sizga 1 martalik test yaratish limiti berildi! (Limit: {settings.onetime_max_students} ta talaba)")
        except:
            pass

@router.message(Command("mod2"))
async def cmd_mod2(message: Message, bot: Bot):
    """/mod2 [ID yoki @username] - standart Premium obuna beradi (30 kun)."""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Formati: `/mod2 [ID yoki @username]`", parse_mode="Markdown")
        return
        
    ident = args[1]
    async with async_session() as session:
        user = await resolve_user_from_ident(session, ident)
        if not user:
            await message.answer(f"❌ `{ident}` topilmadi.", parse_mode="Markdown")
            return
            
        settings = (await session.execute(select(SystemSettings))).scalar()
        
        user.role = "moderator"
        expires_at = local_now() + datetime.timedelta(days=30)
        new_sub = Subscription(
            user_id=user.id,
            type="monthly",
            max_students_limit=settings.monthly_max_students,
            expires_at=expires_at
        )
        session.add(new_sub)
        await session.commit()
        
        await message.answer(f"✅ {user.full_name} ga 30 kunlik Premium berildi (Limit: {settings.monthly_max_students}).")
        try:
            await bot.send_message(user.id, f"🌟 Sizga 1 oylik (30 kunlik) Premium obuna taqdim etildi! (Limit: {settings.monthly_max_students} ta talaba)")
        except:
            pass

@router.message(AdminStates.waiting_for_mod_id)
async def process_mod_id_step(message: Message, state: FSMContext):
    ident = message.text.strip()
    async with async_session() as session:
        user = await resolve_user_from_ident(session, ident)
        if not user:
            await message.answer("❌ Noto'g'ri ID yoki username. Username oldidan @ belgisini qo'ying.")
            return
        await process_mod_target(message, user.id, state)


async def process_mod_target(message: Message, target_id: int, state: FSMContext):
    async with async_session() as session:
        user = await session.get(User, target_id)
        if not user:
            await message.answer(f"❌ ID `{target_id}` ga ega foydalanuvchi bazada topilmadi. Avval u botga kirgan bo'lishi kerak.", parse_mode="Markdown")
            return
        
        sub_stmt = select(Subscription).where(Subscription.user_id == target_id)
        sub_res = await session.execute(sub_stmt)
        subs = sub_res.scalars().all()

        quiz_count_res = await session.execute(select(func.count(Quiz.id)).where(Quiz.teacher_id == target_id))
        quiz_count = quiz_count_res.scalar()

        is_premium = False
        tickets = 0
        expires_str = "Yo'q"
        max_students_override = "Standart (Global)"

        for s in subs:
            if s.type == "monthly" and s.expires_at and s.expires_at > local_now():
                is_premium = True
                expires_str = s.expires_at.strftime("%Y-%m-%d %H:%M")
            if s.type == "onetime":
                tickets += s.credits
            if s.max_students_limit is not None:
                max_students_override = f"{s.max_students_limit} ta (Maxsus)"

        status_text = "Oddiy Foydalanuvchi"
        if user.role == "admin":
            status_text = "Super Admin"
        elif user.role == "moderator" or is_premium or tickets > 0:
            status_text = "Moderator"

        text = (
            f"👤 <b>Foydalanuvchi Ma'lumotlari:</b>\n\n"
            f"<b>Ismi:</b> {user.full_name}\n"
            f"<b>Username:</b> @{user.username if user.username else 'Yoq'}\n"
            f"<b>ID:</b> <code>{user.id}</code>\n"
            f"<b>Status:</b> {status_text}\n"
            f"<b>Yaratgan testlari:</b> {quiz_count} ta\n"
            f"<b>Ro'yxatdan o'tgan:</b> {user.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"💳 <b>Joriy Obunalar va Ruxsatlar:</b>\n"
            f"⏳ Premium muddati: {expires_str}\n"
            f"🎟 Qolgan limitlar: {tickets} ta\n"
            f"👥 O'quvchilar limiti: {max_students_override}\n\n"
            f"👇 <b>Qanday amal bajaramiz?</b>"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Vaqt qo'shish (Premium)", callback_data=f"modact_time_{target_id}")],
            [InlineKeyboardButton(text="🎟 Limit qo'shish", callback_data=f"modact_tickets_{target_id}")],
            [InlineKeyboardButton(text="❌ Ruxsatlarni bekor qilish", callback_data=f"modact_revoke_{target_id}")],
        ])

        await state.clear()
        if isinstance(message, Message):
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("modact_"))
async def cb_modact(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    action = data_parts[1]
    target_id = int(data_parts[2])

    if action == "revoke":
        async with async_session() as session:
            user = await session.get(User, target_id)
            if user:
                user.role = "student"
                await session.execute(delete(Subscription).where(Subscription.user_id == target_id))
                await session.commit()
                await callback.answer("✅ Barcha moderatorlik huquqlari va obunalar o'chirildi!", show_alert=True)
                await process_mod_target(callback, target_id, state)
        return

    await state.update_data(mod_target_id=target_id)

    if action == "time":
        await state.set_state(AdminStates.waiting_for_mod_time)
        await callback.message.answer("⏳ **Necha kunlik ruxsat bermoqchisiz?**\n\nFaqat raqam kiriting (masalan: 30):", parse_mode="Markdown")
        await callback.answer()
    elif action == "tickets":
        await state.set_state(AdminStates.waiting_for_mod_tickets)
        await callback.message.answer("🎟 **Nechta test yaratishga ruxsat bermoqchisiz?**\n\nFaqat raqam kiriting (masalan: 5):", parse_mode="Markdown")
        await callback.answer()

@router.message(AdminStates.waiting_for_mod_time)
async def process_mod_time(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    days = int(message.text)
    await state.update_data(mod_val=days, mod_type="monthly")
    await ask_mod_students_limit(message, state)

@router.message(AdminStates.waiting_for_mod_tickets)
async def process_mod_tickets(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    tickets = int(message.text)
    await state.update_data(mod_val=tickets, mod_type="onetime")
    await ask_mod_students_limit(message, state)

async def ask_mod_students_limit(message: Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_mod_students_limit)
    await message.answer(
        "👥 **Ushbu foydalanuvchi bitta testga eng ko'pi bilan nechta o'quvchi qo'sha olsin?**\n\n"
        "_Tizimdagi standart (global) tarif limitidan foydalanish uchun 0 yozing._",
        parse_mode="Markdown"
    )

@router.message(AdminStates.waiting_for_mod_students_limit)
async def process_mod_students_limit(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    
    limit = int(message.text)
    limit_val = limit if limit > 0 else None

    data = await state.get_data()
    target_id = data["mod_target_id"]
    val = data["mod_val"]
    m_type = data["mod_type"]

    async with async_session() as session:
        user = await session.get(User, target_id)
        if not user:
            return

        user.role = "moderator"
        
        # Oylik bo'lsa, eskisini topish yoki uzaytirish
        if m_type == "monthly":
            sub_res = await session.execute(select(Subscription).where(
                Subscription.user_id == target_id,
                Subscription.type == "monthly"
            ))
            sub = sub_res.scalar_one_or_none()
            if not sub:
                sub = Subscription(user_id=target_id, type="monthly")
                session.add(sub)
            
            if not sub.expires_at or sub.expires_at < local_now():
                sub.expires_at = local_now() + datetime.timedelta(days=val)
            else:
                sub.expires_at = sub.expires_at + datetime.timedelta(days=val)
            
            sub.max_students_limit = limit_val

        elif m_type == "onetime":
            sub_res = await session.execute(select(Subscription).where(
                Subscription.user_id == target_id,
                Subscription.type == "onetime"
            ))
            sub = sub_res.scalar_one_or_none()
            if not sub:
                sub = Subscription(user_id=target_id, type="onetime", credits=0)
                session.add(sub)
            
            sub.credits += val
            sub.max_students_limit = limit_val

        await session.commit()
        
        await message.answer(f"✅ Ruxsatlar muvaffaqiyatli saqlandi!")
        
        # Xabarnoma
        try:
            msg = f"🎉 **Tabriklaymiz! Bosh Admin tomonidan sizga Moderatorlik huquqi taqdim etildi.**"
            await bot.send_message(target_id, msg, parse_mode="Markdown")
        except:
            pass

    await process_mod_target(message, target_id, state)
import pandas as pd
import io
from aiogram.types import BufferedInputFile

def get_authorized_users_data(users, subs, quiz_counts):
    subs_by_user = {}
    for s in subs:
        if s.user_id not in subs_by_user:
            subs_by_user[s.user_id] = []
        subs_by_user[s.user_id].append(s)

    data = []
    for u in users:
        is_premium = False
        is_demo = False
        demo_expires_str = ""
        tickets = 0
        expires_str = "Yo'q"
        max_students = "Global"

        u_subs = subs_by_user.get(u.id, [])
        for s in u_subs:
            if s.type == "monthly" and s.expires_at and s.expires_at > local_now():
                is_premium = True
                expires_str = s.expires_at.strftime("%Y-%m-%d %H:%M")
            if s.type == "free_demo" and s.expires_at and s.expires_at > local_now():
                is_demo = True
                demo_expires_str = s.expires_at.strftime("%Y-%m-%d %H:%M")
            if s.type == "onetime":
                tickets += s.credits
            if s.max_students_limit is not None:
                max_students = str(s.max_students_limit)
        
        status = "Foydalanuvchi"
        if u.role == "admin":
            status = "Super Admin"
        elif is_premium or tickets > 0 or u.role == "moderator":
            status = "Moderator"
        elif is_demo:
            status = "Demo"

        # Faqat adminlar va ruxsati borlarni ko'rsatamiz
        if status == "Foydalanuvchi":
            continue

        data.append({
            "id": u.id,
            "full_name": u.full_name,
            "username": f"@{u.username}" if u.username else "Yo'q",
            "role": status,
            "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
            "quiz_count": quiz_counts.get(u.id, 0),
            "premium_expires": expires_str,
            "demo_expires": demo_expires_str if is_demo else "Yo'q",
            "tickets": tickets,
            "max_students": max_students
        })
    return data


@router.message(Command("users", "foydalanuvchilar"))
async def cmd_show_users_list(message: Message):
    """Barcha faol (ruxsati bor) foydalanuvchilarning matnli ro'yxatini va Excel yuklab olish tugmasini chiqarish."""
    if message.from_user.id not in ADMIN_IDS:
        return

    async with async_session() as session:
        users = (await session.execute(select(User))).scalars().all()
        if not users:
            await message.answer("Bazada foydalanuvchilar yo'q.")
            return
            
        subs = (await session.execute(select(Subscription))).scalars().all()
        quiz_counts_res = await session.execute(select(Quiz.teacher_id, func.count(Quiz.id)).group_by(Quiz.teacher_id))
        quiz_counts = {row[0]: row[1] for row in quiz_counts_res.all()}

    auth_users = get_authorized_users_data(users, subs, quiz_counts)
    
    if not auth_users:
        await message.answer("Tizimda hozircha birorta ham Moderator yoki Admin topilmadi.")
        return

    # Matnli ro'yxat tuzamiz
    text_lines = ["👥 <b>RUXSATI BOR FOYDALANUVCHILAR RO'YXATI:</b>\n"]
    
    for idx, u in enumerate(auth_users, start=1):
        # Qisqacha ma'lumot qatori
        time_info = "Cheksiz"
        if u['role'] == "Demo":
            time_info = f"⏳ Demo: {u['demo_expires']}"
        elif u['role'] == "Moderator":
            time_info = f"⏳ Prem: {u['premium_expires']} | 🎟 {u['tickets']} ta"
        
        limit_info = f"👥 Limit: {u['max_students']}"
        
        line = f"<b>{idx}.</b> {u['username']} | <b>{u['role']}</b>\n└ {time_info} | {limit_info}"
        text_lines.append(line)
        
        # Agar 4096 belgidan oshib ketsa, qisqartiramiz
        if len("\n\n".join(text_lines)) > 3500:
            text_lines.append("\n<i>...va hokazo. To'liq ma'lumotni Excel orqali yuklab oling!</i>")
            break

    msg_text = "\n\n".join(text_lines)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel formatda yuklab olish", callback_data="export_users_excel")]
    ])
    
    await message.answer(msg_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "export_users_excel")
async def cb_export_users_excel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
        
    await callback.answer("Fayl tayyorlanmoqda...", show_alert=False)

    async with async_session() as session:
        users = (await session.execute(select(User))).scalars().all()
        subs = (await session.execute(select(Subscription))).scalars().all()
        quiz_counts_res = await session.execute(select(Quiz.teacher_id, func.count(Quiz.id)).group_by(Quiz.teacher_id))
        quiz_counts = {row[0]: row[1] for row in quiz_counts_res.all()}

    auth_users = get_authorized_users_data(users, subs, quiz_counts)

    # Excel ustunlari uchun
    excel_data = []
    for u in auth_users:
        excel_data.append({
            "ID": u["id"],
            "F.I.Sh": u["full_name"],
            "Username": u["username"],
            "Rol/Holat": u["role"],
            "Ro'yxatdan o'tgan": u["created_at"],
            "Yaratgan testlari": u["quiz_count"],
            "Premium Muddati": u["premium_expires"],
            "Demo Muddati": u["demo_expires"],
            "Qolgan Limitlar": u["tickets"],
            "O'quvchilar Limiti": u["max_students"]
        })

    df = pd.DataFrame(excel_data)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Foydalanuvchilar')
    excel_buffer.seek(0)
    
    file = BufferedInputFile(excel_buffer.read(), filename=f"foydalanuvchilar_{local_now().strftime('%Y%m%d_%H%M')}.xlsx")
    await callback.message.answer_document(
        document=file,
        caption="📊 **To'liq ro'yxat (Excel fayl)**",
        parse_mode="Markdown"
    )
