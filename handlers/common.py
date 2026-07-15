from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func

from config import ADMIN_IDS
from database import async_session, User, Student, Quiz, SystemSettings
from keyboards.bot_keyboards import get_welcome_kb, get_teacher_menu, get_student_menu, get_admin_menu
from states import AuthStates, TeacherStates, StudentStates

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    /start buyrug'i. Foydalanuvchining roliga qarab uni tegishli menyuga yo'naltiradi.
    Deep-linking (t.me/bot?start=quiz_code) orqali studentlarni test kodisiz kiritadi.
    """
    await state.clear()
    user_id = message.from_user.id

    # Deep linking tekshiruvi (start buyrug'i bilan birga test kodi kelgan bo'lsa)
    args = message.text.split()
    deep_code = None
    if len(args) > 1:
        deep_code = args[1].strip()

    # Referal havola tekshiruvi
    referrer_id = None
    if deep_code and deep_code.startswith("ref_"):
        try:
            referrer_id = int(deep_code.replace("ref_", ""))
        except ValueError:
            pass

    # Xodimlarning talaba bo'lib kirib qolishi (Double-role) deadlock oldini olish
    async with async_session() as session:
        user_stmt = select(User).where(User.id == user_id)
        db_user = (await session.execute(user_stmt)).scalar_one_or_none()

        student_stmt = select(Student).where(Student.telegram_id == user_id)
        student = (await session.execute(student_stmt)).scalar_one_or_none()

        # Agar yangi foydalanuvchi bo'lsa va referal havola orqali kirgan bo'lsa
        if db_user is None and student is None and referrer_id is not None:
            if referrer_id != user_id:
                # Taklif qilgan ustozni olish
                ref_user_stmt = select(User).where(User.id == referrer_id)
                ref_user = (await session.execute(ref_user_stmt)).scalar_one_or_none()
                if ref_user:
                    from database import Subscription
                    from config import local_now
                    
                    # Ustozning faol obunalarini tekshirish (muzlatish shartini tekshirish uchun)
                    ref_subs_stmt = select(Subscription).where(Subscription.user_id == referrer_id)
                    ref_subs = (await session.execute(ref_subs_stmt)).scalars().all()
                    
                    is_premium = any(s.type == "monthly" and s.expires_at > local_now() for s in ref_subs)
                    has_credits = any(s.type in ("onetime", "free_demo") and s.credits > 0 for s in ref_subs)
                    
                    # Agar ustozda faol limit yoki premium bo'lmasa, taklifni inobatga olamiz
                    if not is_premium and not has_credits:
                        if ref_user.referral_count < 5:
                            ref_user.referral_count += 1
                            if ref_user.referral_count == 5:
                                # Bonus limit berish
                                bonus_sub = Subscription(
                                    user_id=referrer_id,
                                    type="onetime",
                                    credits=1
                                )
                                session.add(bonus_sub)
                                
                                # Ustozga xabar berish
                                try:
                                    await message.bot.send_message(
                                        chat_id=referrer_id,
                                        text="🎉 **Tabriklaymiz!** Siz taklif qilgan yangi a'zolar soni 5 taga yetdi va sizga **1 ta bepul test yaratish limiti** (onetime) taqdim etildi!",
                                        parse_mode="Markdown"
                                    )
                                except Exception:
                                    pass
                    
            # Yangi mehmon profilini yaratib qo'yamiz (takroriy referal qo'shilishining oldini olish uchun)
            new_guest = User(
                id=user_id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                role="guest",
                referrer_id=referrer_id
            )
            session.add(new_guest)
            await session.commit()
            db_user = new_guest

        if student and (db_user or user_id in ADMIN_IDS):
            role_text = "Admin" if (user_id in ADMIN_IDS or (db_user and db_user.role == "admin")) else "Moderator"
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Talaba rejimidan chiqish", callback_data="switch_logout_student")],
                    [InlineKeyboardButton(text=f"{role_text} paneliga o'tish", callback_data="switch_to_staff")]
                ]
            )
            await message.answer(
                f"Siz talaba sifatida tizimga kirgansiz, lekin ayni paytda {role_text}siz.\n\n"
                f"Qaysi rejimga o'tishni xohlaysiz?",
                reply_markup=kb,
                parse_mode="Markdown"
            )
            return

    # 1. Super Admin/Admin tekshiruvi (hardcoded list orqali)
    if user_id in ADMIN_IDS:
        async with async_session() as session:
            # Adminni bazada profilini yaratish yoki yangilash
            db_user = await session.get(User, user_id)
            if not db_user:
                admin_user = User(
                    id=user_id,
                    full_name=message.from_user.full_name,
                    username=message.from_user.username,
                    role="admin",
                )
                session.add(admin_user)
                await session.commit()
            elif db_user.role != "admin":
                db_user.role = "admin"
                await session.commit()

        await message.answer(
            f"Salom, Bosh Admin!\nTizim boshqaruv paneliga xush kelibsiz.",
            reply_markup=get_admin_menu(),
        )
        return

    # 2. Student active session (Eng yuqori ustuvorlik)
    async with async_session() as session:
        student_stmt = select(Student).where(Student.telegram_id == user_id)
        student_res = await session.execute(student_stmt)
        student = student_res.scalar_one_or_none()

        if student:
            # Student test holatida faol sessiyasi bor
            # Test holatini tekshirish
            quiz = await session.get(Quiz, student.quiz_id)
            if quiz and quiz.status == "active":
                # Test yechilayotgan paytda uzilib kirdi, davom ettirish
                await message.answer(
                    f"Salom {student.full_name}!\nSizda faol test topshirish jarayoni mavjud. Davom ettirishingiz mumkin.",
                    reply_markup=get_student_menu(),
                )
                # Bu yerda student.py da handlerga yo'naltiramiz
                from keyboards.bot_keyboards import get_student_resume_kb
                await message.answer(
                    "Testni davom ettirish uchun tugmani bosing:",
                    reply_markup=get_student_resume_kb(),
                )
            else:
                # Test kutilmoqda (lobbyda)
                await message.answer(
                    f"Salom {student.full_name}!\nSiz tizimdasiz. Moderator testni boshlashini kuting...",
                    reply_markup=get_student_menu(),
                )
                await state.set_state(StudentStates.waiting_to_start)
            return

    # 3. Moderator tekshiruvi
    async with async_session() as session:
        teacher_stmt = select(User).where(User.id == user_id, User.role == "moderator")
        teacher_res = await session.execute(teacher_stmt)
        teacher = teacher_res.scalar_one_or_none()

        if teacher:
            # Qoidalar: testlar sonini tekshiramiz
            quiz_count_stmt = select(func.count(Quiz.id)).where(Quiz.teacher_id == user_id)
            quiz_count_res = await session.execute(quiz_count_stmt)
            quiz_count = quiz_count_res.scalar()

            # Agar u moderator bo'lsa va obuna/chiptalari bor bo'lsa yoki test yaratgan bo'lsa (2/3-holat)
            # Uni avtomatik moderator menyusiga kiritamiz
            if quiz_count > 0:
                await message.answer(
                    f"Salom {teacher.full_name}! Moderatorlik kabinetiga qaytdingiz.",
                    reply_markup=get_teacher_menu(is_demo=False),
                )
                return
            else:
                # Test yaratmagan bo'lsa (1-holat) - vaqtincha yozuvi o'chadi va mehmonga qaytadi
                await session.delete(teacher)
                await session.commit()
                # Keyingi qadamda salomlashish oynasi ochiladi

    # 4. Deep linking orqali student login oynasiga to'g'ridan-to'g'ri o'tkazish
    if deep_code:
        # Kodni tekshirish
        async with async_session() as session:
            stmt = select(Quiz).where(Quiz.code == deep_code)
            res = await session.execute(stmt)
            quiz = res.scalar_one_or_none()

            if quiz:
                if quiz.status == "completed":
                    await message.answer("⚠️ Ushbu test yakunlangan! Uni yechib bo'lmaydi.")
                else:
                    await state.update_data(quiz_code=deep_code, quiz_db_id=quiz.id)
                    await state.set_state(AuthStates.waiting_for_student_login)
                    await message.answer(
                        f"📚 Test: *{quiz.title}*\n\nUshbu testga kirish uchun o'qituvchingiz bergan *Login*ni kiriting:",
                        parse_mode="Markdown",
                    )
                    return
            else:
                await message.answer("⚠️ Yaroqsiz test kodi yuborildi.")

    # 5. Mehmon (Yangi foydalanuvchi)
    # Tizim texnik ishlar rejimida ekanligini tekshirish
    async with async_session() as session:
        settings_res = await session.execute(select(SystemSettings))
        settings = settings_res.scalar()
        if settings and settings.maintenance_mode:
            await message.answer(
                "Tizimda texnik ishlar olib borilmoqda.\nTez orada bot faoliyati tiklanadi. Noqulayliklar uchun uzr so'raymiz!",
                parse_mode="Markdown",
            )
            return

    await message.answer(
        "Assalomu alaykum! Tizimga xush kelibsiz.\n\n"
        "Ushbu tizim o'qituvchilar uchun testlar o'tkazish (oraliq, yakuniy nazorat) uchun juda qulay. Natijalar excel formatda tayyorlab beriladi.\n\n"
        "Davom etish uchun quyidagilardan birini tanlang:",
        reply_markup=get_welcome_kb(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "about_bot")
async def cb_about_bot(callback: CallbackQuery):
    """Bot haqida qisqacha ma'lumot"""
    about_text = (
        "Bot haqida ma'lumot:\n\n"
        "Tizim orqali o'qituvchilar Word faylidagi test variantlari va talabalar ro'yxatini yuklab, osongina "
        "kiberhimoyalangan, sinxron boshlanadigan testlar o'tkazishlari mumkin.\n\n"
        "Asosiy imkoniyatlar:\n"
        "- Talabalar uchun vaqtinchalik login-parol seansi\n"
        "- Savollar va variantlar aralashuvi\n"
        "- Imtihonni jonli kuzatish\n"
        "- Excel formatida tahliliy hisobot (matritsa va diagnostika)"
    )
    await callback.message.edit_text(about_text, reply_markup=get_welcome_kb(), parse_mode="Markdown")


@router.callback_query(F.data == "switch_logout_student")
async def cb_switch_logout_student(callback: CallbackQuery, state: FSMContext):
    """Xodimni talaba sessiyasidan tozalab chiqarib yuboradi"""
    user_id = callback.from_user.id
    async with async_session() as session:
        stmt = select(Student).where(Student.telegram_id == user_id)
        res = await session.execute(stmt)
        student = res.scalar_one_or_none()
        if student:
            student.telegram_id = None
            await session.commit()

    await state.clear()
    await callback.message.delete()

    # Yangi boshlang'ich start xabari
    from aiogram.types import Message as TelegramMessage
    dummy_msg = TelegramMessage(
        message_id=callback.message.message_id,
        date=callback.message.date,
        chat=callback.message.chat,
        from_user=callback.from_user,
        text="/start"
    )
    await cmd_start(dummy_msg, state)
    await callback.answer("Talaba rejimidan chiqildi.", show_alert=True)


@router.callback_query(F.data == "switch_to_staff")
async def cb_switch_to_staff(callback: CallbackQuery, state: FSMContext):
    """Talaba sessiyasini buzmasdan to'g'ridan-to'g'ri xodim kabinetiga o'tadi"""
    user_id = callback.from_user.id
    await state.clear()
    await callback.message.delete()

    if user_id in ADMIN_IDS:
        await callback.message.answer(
            f"Salom, Bosh Admin!\nTizim boshqaruv paneliga kirdingiz.",
            reply_markup=get_admin_menu(),
        )
    else:
        async with async_session() as session:
            teacher_stmt = select(User).where(User.id == user_id, User.role == "moderator")
            teacher_res = await session.execute(teacher_stmt)
            teacher = teacher_res.scalar_one_or_none()

            if teacher:
                await callback.message.answer(
                    f"Salom {teacher.full_name}! Moderatorlik kabinetiga kirdingiz.",
                    reply_markup=get_teacher_menu(is_demo=False),
                )
            else:
                await callback.message.answer("Siz xodim emassiz.", reply_markup=get_welcome_kb())

    await callback.answer()
