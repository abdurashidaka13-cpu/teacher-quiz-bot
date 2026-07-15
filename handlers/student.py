import datetime
import random
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from sqlalchemy import select, func, update

from config import TIMEZONE, local_now
from database import async_session, Student, Quiz, Question, StudentAttempt, StudentAnswer
from keyboards.bot_keyboards import (
    get_welcome_kb,
    get_student_menu,
    get_student_answer_kb,
    get_student_start_exam_kb,
    get_cancel_kb,
)
from states import AuthStates, StudentStates

router = Router(name="student")


# ==========================================
# 1. STUDENT TIZIMGA KIRISH (LOGIN-PAROL)
# ==========================================
@router.callback_query(F.data == "auth_student")
async def cb_student_login_start(callback: CallbackQuery, state: FSMContext):
    """Student login so'rash oynasini ochish - avval test kodini so'rash"""
    await state.set_state(AuthStates.waiting_for_quiz_code)
    await callback.message.delete()  # Eski inline menyuni o'chiramiz
    await callback.message.answer(
        "🔑 **Student tizimiga kirish**\n\nIltimos, o'qituvchingiz bergan **Test kodi**ni (6 xonali son) kiriting:",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(AuthStates.waiting_for_quiz_code)
async def process_quiz_code(message: Message, state: FSMContext):
    """Kiritilgan test kodini tekshirish"""
    code = message.text.strip()
    if code in ["Tizimdan chiqish", "Bekor qilish", "/start"]:
        await state.clear()
        from handlers.common import cmd_start
        await cmd_start(message, state)
        return

    async with async_session() as session:
        stmt = select(Quiz).where(Quiz.code == code)
        res = await session.execute(stmt)
        quiz = res.scalar_one_or_none()

        if not quiz:
            await message.answer("⚠️ Yaroqsiz test kodi kiritildi. Qaytadan urinib ko'ring yoki bekor qiling:")
            return

        if quiz.status == "completed":
            await message.answer("⚠️ Ushbu test allaqachon yakunlangan! Uni yechib bo'lmaydi.")
            return

        await state.update_data(quiz_code=code, quiz_db_id=quiz.id)
        await state.set_state(AuthStates.waiting_for_student_login)
        await message.answer(
            f"📚 Test: *{quiz.title}*\n\nEndi o'qituvchingiz bergan **Login**ni kiriting:",
            reply_markup=get_cancel_kb(),
            parse_mode="Markdown",
        )


@router.message(AuthStates.waiting_for_student_login)
async def process_student_login(message: Message, state: FSMContext):
    """Loginni saqlash va parolni so'rash"""
    login = message.text.strip()
    if login in ["🚪 Chiqish (Log out)", "🔙 Bekor qilish", "/start"]:
        await state.clear()
        from handlers.common import cmd_start
        await cmd_start(message, state)
        return

    if not login:
        await message.answer("Login bo'sh bo'lishi mumkin emas. Kiriting:")
        return

    await state.update_data(student_login=login)
    await state.set_state(AuthStates.waiting_for_student_password)
    await message.answer("🔑 Endi parolingizni kiriting:", reply_markup=get_cancel_kb())


@router.message(AuthStates.waiting_for_student_password)
async def process_student_password(message: Message, state: FSMContext):
    """Login va parolni tekshirish, sessiyani band qilish (hash solishtirish)"""
    password = message.text.strip()
    if password in ["Tizimdan chiqish", "Bekor qilish", "/start"]:
        await state.clear()
        from handlers.common import cmd_start
        await cmd_start(message, state)
        return

    data = await state.get_data()
    login = data.get("student_login")
    quiz_db_id = data.get("quiz_db_id")
    user_id = message.from_user.id

    if not quiz_db_id:
        await message.answer("⚠️ Tizim xatoligi (sessiya topilmadi). Boshidan kirishni boshlang.", reply_markup=get_welcome_kb())
        await state.clear()
        return

    import bcrypt

    async with async_session() as session:
        # Studentni faqat login va quiz_id bo'yicha qidirish
        stmt = select(Student).where(
            Student.login == login,
            Student.quiz_id == quiz_db_id
        )
        res = await session.execute(stmt)
        student = res.scalar_one_or_none()

        # Parolni tekshirish
        if student:
            try:
                # Bcrypt bilan tekshirish
                if not bcrypt.checkpw(password.encode(), student.password.encode("utf-8")):
                    student = None
            except ValueError:
                # Agar bcrypt formati noto'g'ri bo'lsa (ya'ni eski SHA256 bo'lsa), eski usulda tekshiramiz
                import hashlib
                hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                if student.password != hashed_pw:
                    student = None
        
        if not student:
            await message.answer(
                "❌ **Login yoki parol noto'g'ri!**\n\nIltimos, qaytadan boshidan urinib ko'ring.\n"
                "Loginni kiriting:",
                reply_markup=get_cancel_kb(),
                parse_mode="Markdown",
            )
            await state.set_state(AuthStates.waiting_for_student_login)
            return

        # Sessiya bandligini tekshirish (Phone Sharing)
        # Agar ushbu login boshqa Telegram profildan faol bo'lsa, kiritmaydi
        if student.telegram_id is not None and student.telegram_id != user_id:
            await message.answer(
                "⚠️ **Sessiya band!**\nUshbu login boshqa telefon orqali faol yechilmoqda.\n"
                "Bir vaqtda faqat bitta telefondan kirish mumkin.",
            )
            await state.clear()
            await message.answer("Bosh sahifaga qaytdingiz.", reply_markup=get_welcome_kb())
            return

        # Urinish tugallanganligini tekshirish (Bir marta topshirish qoidasi)
        attempt_stmt = select(StudentAttempt).where(
            StudentAttempt.student_id == student.id, StudentAttempt.completed_at.isnot(None)
        )
        attempt_res = await session.execute(attempt_stmt)
        completed_attempt = attempt_res.scalar_one_or_none()

        if completed_attempt:
            await message.answer(
                "❌ **Siz ushbu testni topshirib bo'lgansiz!**\n"
                "Qayta topshirishga ruxsat yo'q.",
            )
            await state.clear()
            await message.answer("Bosh sahifaga qaytdingiz.", reply_markup=get_welcome_kb())
            return

        # Test holatini tekshirish
        quiz = await session.get(Quiz, student.quiz_id)
        if not quiz:
            await message.answer("Xatolik: Ushbu studentga biriktirilgan test topilmadi.")
            return

        if quiz.status == "completed":
            await message.answer("⚠️ Ushbu imtihon allaqachon yakunlangan!")
            await state.clear()
            await message.answer("Bosh sahifaga qaytdingiz.", reply_markup=get_welcome_kb())
            return

        # Telegram ID ni bog'lash (Sessiya boshlash)
        student.telegram_id = user_id
        student.logged_in_at = local_now()
        await session.commit()

        # FSM ma'lumotlarini saqlash
        await state.update_data(student_db_id=student.id, quiz_db_id=quiz.id)

        if quiz.status == "waiting":
            # Kutish zalida (Lobby)
            await state.set_state(StudentStates.waiting_to_start)
            await message.answer(
                f"✅ **Muvaffaqiyatli kirdingiz!**\n"
                f"📚 Test: *{quiz.title}*\n"
                f"👤 Student: *{student.full_name}*\n\n"
                f"⏳ Moderator imtihonni boshlashini kuting. Dars boshlanganda start xabari olasiz.",
                reply_markup=get_student_menu(),
                parse_mode="Markdown",
            )
        elif quiz.status == "active":
            # Imtihon allaqachon faol, start beramiz
            await state.set_state(StudentStates.waiting_to_start)
            await message.answer(
                f"✅ **Muvaffaqiyatli kirdingiz!**\n"
                f"📚 Test: *{quiz.title}*\n\n"
                f"Imtihon faol holatda. Boshlash uchun tugmani bosing:",
                reply_markup=get_student_start_exam_kb(quiz.code),
                parse_mode="Markdown",
            )


# ==========================================
# 2. STUDENT LOBBYDAN CHIQISH (LOGOUT)
# ==========================================
@router.message(F.text == "Tizimdan chiqish")
async def process_student_logout(message: Message, state: FSMContext):
    """Student sessiyasidan chiqish (Lobbyda)"""
    user_id = message.from_user.id
    current_state = await state.get_state()

    async with async_session() as session:
        # Telegram ID bo'yicha studentni topish
        stmt = select(Student).where(Student.telegram_id == user_id)
        res = await session.execute(stmt)
        student = res.scalar_one_or_none()

        if student:
            # Agar imtihon jarayoni ketayotgan bo'lsa, chiqib ketish ballni yakunlaydi!
            if current_state == StudentStates.solving_quiz.state:
                # Faol urinishni tugatish
                att_stmt = select(StudentAttempt).where(
                    StudentAttempt.student_id == student.id, StudentAttempt.completed_at.is_(None)
                )
                att_res = await session.execute(att_stmt)
                attempt = att_res.scalar_one_or_none()

                if attempt:
                    attempt.completed_at = local_now()
                    # To'g'ri javoblarni hisoblash
                    ans_stmt = select(StudentAnswer).where(StudentAnswer.attempt_id == attempt.id)
                    ans_res = await session.execute(ans_stmt)
                    answers = ans_res.scalars().all()

                    correct_count = sum(1 for a in answers if a.is_correct)
                    attempt.score = correct_count
                    attempt.total_questions = len(answers)

                # Sessiyani yopish
                student.telegram_id = None
                await session.commit()
                await state.clear()
                await message.answer(
                    f"⚠️ Test jarayonidan chiqdingiz. Imtihoningiz yakunlandi!\n"
                    f"Natijangiz: {correct_count}/{len(answers)} ball.",
                    reply_markup=get_welcome_kb(),
                )
                return
            else:
                # Kutish zalida turgan bo'lsa (Lobbyda) - oddiy chiqish
                student.telegram_id = None
                await session.commit()
                await state.clear()
                await message.answer(
                    "Tizimdan chiqdingiz. Login boshqa telefon uchun bo'shatildi.",
                    reply_markup=get_welcome_kb(),
                )
                return

    await state.clear()
    await message.answer("Bosh sahifaga qaytdingiz.", reply_markup=get_welcome_kb())


# ==========================================
# 3. IMTIHONNI BOSHLASH & DOUBLE-SHUFFLE
# ==========================================
@router.callback_query(F.data.startswith("start_exam_"))
async def cb_start_exam(callback: CallbackQuery, state: FSMContext):
    """
    Imtihon topshirishni boshlash.
    Urinish yaratadi va savollarni Double-Shuffle qiladi.
    """
    user_id = callback.from_user.id
    quiz_code = callback.data.split("_")[2]

    async with async_session() as session:
        # Studentni olish
        stud_stmt = select(Student).where(Student.telegram_id == user_id)
        stud_res = await session.execute(stud_stmt)
        student = stud_res.scalar_one_or_none()

        if not student:
            await callback.answer("Siz faol talaba emassiz!", show_alert=True)
            return

        # Testni olish
        quiz = await session.get(Quiz, student.quiz_id)
        if not quiz or quiz.status != "active":
            await callback.answer("Imtihon faol emas!", show_alert=True)
            return

        # Urinish bormi?
        att_stmt = select(StudentAttempt).where(StudentAttempt.student_id == student.id)
        att_res = await session.execute(att_stmt)
        attempt = att_res.scalar_one_or_none()

        if attempt:
            await callback.answer("Siz allaqachon urinish boshlagansiz!", show_alert=True)
            return

        # 1. Yangi Urinish yaratish
        new_attempt = StudentAttempt(
            student_id=student.id,
            started_at=local_now(),
        )
        session.add(new_attempt)
        await session.flush()  # ID ni olish uchun

        # 2. Savollarni chalkashtirish (Double-Shuffle)
        # Faol variantlarga mos savollarni olish
        active_vars = quiz.active_variants  # JSONB list
        q_stmt = select(Question).where(
            Question.quiz_id == quiz.id, Question.variant.in_(active_vars)
        )
        q_res = await session.execute(q_stmt)
        questions = q_res.scalars().all()

        if not questions:
            await callback.answer("Xatolik: Savollar topilmadi!", show_alert=True)
            return

        # 1-Shuffle: Savollar tartibini chalkashtirish
        random.shuffle(questions)

        # Agar o'qituvchi ma'lum miqdordagi savollarni ko'rsatishni so'ragan bo'lsa
        if quiz.questions_to_show and quiz.questions_to_show > 0:
            questions = questions[:quiz.questions_to_show]

        # 3. Student javoblar jadvalini to'ldirish
        for order_idx, q in enumerate(questions, 1):
            # 2-Shuffle: Variantlar (to'g'ri va noto'g'ri) o'rnini chalkashtirish
            options = [q.correct_answer] + q.distractors  # 4 ta variant (Strict 4 options)
            random.shuffle(options)

            new_answer = StudentAnswer(
                attempt_id=new_attempt.id,
                question_id=q.id,
                order_index=order_idx,
                shuffled_options=options,
            )
            session.add(new_answer)

        await session.commit()

    # Yechish holatiga o'tkazish
    await state.set_state(StudentStates.solving_quiz)
    await state.update_data(
        attempt_id=new_attempt.id,
        current_question_idx=1,
        total_questions=len(questions),
    )

    await callback.message.delete()
    await callback.answer()

    # Birinchi savolni ko'rsatish
    await show_student_question(callback.message.chat.id, state, callback.bot)


# ==========================================
# 4. SAVOLLARNI KO'RSATISH FUNKSIYASI (JONLI)
# ==========================================
async def show_student_question(chat_id: int, state: FSMContext, bot: Bot):
    """Studentga navbatdagi savolni rasm va variantlari bilan jo'natadi"""
    data = await state.get_data()
    attempt_id = data["attempt_id"]
    q_idx = data["current_question_idx"]
    total_q = data["total_questions"]

    async with async_session() as session:
        # Savolni student_answers dan topish
        stmt = select(StudentAnswer).where(
            StudentAnswer.attempt_id == attempt_id, StudentAnswer.order_index == q_idx
        )
        res = await session.execute(stmt)
        stud_answer = res.scalar_one_or_none()

        if not stud_answer:
            await state.clear()
            return

        # Asl savol matnini va rasmini olish
        question = await session.get(Question, stud_answer.question_id)

    # Savol matnini tayyorlash
    options = stud_answer.shuffled_options
    options_text = ""
    for idx, opt in enumerate(options):
        char = chr(65 + idx)  # A, B, C, D
        options_text += f"**{char})** {opt}\n"

    msg_text = (
        f"📝 **Savol: {q_idx} / {total_q}**\n\n"
        f"{question.question_text}\n\n"
        f"{options_text}"
    )

    # Dynamic keyboard options count
    kb = get_student_answer_kb(q_idx, len(options))

    # Rasm bor-yo'qligini tekshirish
    if question.image_data:
        photo = BufferedInputFile(question.image_data, filename="question.webp")
        await bot.send_photo(chat_id, photo, caption=msg_text, reply_markup=kb, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id, msg_text, reply_markup=kb, parse_mode="Markdown")


# ==========================================
# 5. JAVOBLAR CALLBACK HODISASI
# ==========================================
@router.callback_query(StudentStates.solving_quiz, F.data.startswith("ans_"))
async def cb_process_answer(callback: CallbackQuery, state: FSMContext):
    """Student variant tanlaganida uning javobini saqlab, keyingisiga o'tkazadi"""
    args = callback.data.split("_")
    q_idx = int(args[1])
    option_idx = int(args[2])

    data = await state.get_data()
    attempt_id = data["attempt_id"]
    current_q_idx = data["current_question_idx"]
    total_q = data["total_questions"]

    # Failsafe: agar tugma eski bo'lsa yoki chalkashib ketsa
    if q_idx != current_q_idx:
        await callback.answer()
        return

    async with async_session() as session:
        # Urinishni olish (Vaqtni tekshirish uchun)
        attempt = await session.get(StudentAttempt, attempt_id)
        student = await session.get(Student, attempt.student_id)
        quiz = await session.get(Quiz, student.quiz_id)

        # Vaqt tugaganini tekshirish (Server-side vaqt tekshiruvi)
        now = local_now()
        end_time = quiz.end_time if quiz.end_time else now

        if quiz.status != "active" or now > end_time:
            # Imtihon tugagan, urinishni tugatish
            attempt.completed_at = now
            student.telegram_id = None  # Auto-logout

            # Jami ballni hisoblash
            answers = await session.scalars(
                select(StudentAnswer).where(StudentAnswer.attempt_id == attempt_id)
            )
            answers = answers.all()
            correct_count = sum(1 for a in answers if a.is_correct)
            attempt.score = correct_count
            attempt.total_questions = len(answers)

            await session.commit()
            await state.clear()
            await callback.message.delete()
            await callback.message.answer(
                f"⏰ **Vaqt tugadi!**\n\nImtihon yakunlandi. Natijangiz: *{correct_count} / {total_q} ball*.",
                reply_markup=get_welcome_kb(),
                parse_mode="Markdown",
            )
            await callback.answer()
            return

        # StudentAnswer yozuvini yangilash
        ans_stmt = select(StudentAnswer).where(
            StudentAnswer.attempt_id == attempt_id, StudentAnswer.order_index == q_idx
        )
        ans_res = await session.execute(ans_stmt)
        stud_answer = ans_res.scalar_one_or_none()

        if stud_answer:
            # Javobni to'g'ri-xatoligini tekshirish
            selected_answer_text = stud_answer.shuffled_options[option_idx]
            # Asl savolni topish
            question = await session.get(Question, stud_answer.question_id)
            is_correct = (selected_answer_text == question.correct_answer)

            stud_answer.selected_option_index = option_idx
            stud_answer.is_correct = is_correct

            await session.commit()

    # O'chirish
    await callback.message.delete()
    await callback.answer()

    # Keyingi savolga o'tish yoki tugatish
    if q_idx < total_q:
        # Keyingi savolni ko'rsatish
        next_idx = q_idx + 1
        await state.update_data(current_question_idx=next_idx)
        await show_student_question(callback.message.chat.id, state, callback.bot)
    else:
        # Test tamom bo'ldi!
        async with async_session() as session:
            attempt = await session.get(StudentAttempt, attempt_id)
            student = await session.get(Student, attempt.student_id)

            attempt.completed_at = local_now()
            student.telegram_id = None  # Auto-logout (sessiyani bo'shatish)

            # Jami ballni hisoblash
            answers = await session.scalars(
                select(StudentAnswer).where(StudentAnswer.attempt_id == attempt_id)
            )
            answers = answers.all()
            correct_count = sum(1 for a in answers if a.is_correct)
            attempt.score = correct_count
            attempt.total_questions = len(answers)

            await session.commit()

        await state.clear()
        await callback.message.answer(
            f"🎉 **Tabriklaymiz! Testni muvaffaqiyatli yakunladingiz.**\n\n"
            f"👤 Student: *{student.full_name}*\n"
            f"✅ Natijangiz: *{correct_count} / {total_q} ball*.",
            reply_markup=get_welcome_kb(),
            parse_mode="Markdown",
        )


# ==========================================
# 6. KIBERXAVFSIZLIK - DAVOM ETTIRISH (RESUME)
# ==========================================
@router.callback_query(F.data == "resume_exam")
async def cb_resume_exam(callback: CallbackQuery, state: FSMContext):
    """Student interneti uzilib qolganda testni qolgan joyidan xavfsiz davom ettiradi"""
    user_id = callback.from_user.id

    async with async_session() as session:
        # Studentni olish
        stud_stmt = select(Student).where(Student.telegram_id == user_id)
        stud_res = await session.execute(stud_stmt)
        student = stud_res.scalar_one_or_none()

        if not student:
            await callback.answer("Sessiyangiz topilmadi!", show_alert=True)
            return

        # Urinishni olish
        att_stmt = select(StudentAttempt).where(
            StudentAttempt.student_id == student.id, StudentAttempt.completed_at.is_(None)
        )
        att_res = await session.execute(att_stmt)
        attempt = att_res.scalar_one_or_none()

        if not attempt:
            await callback.answer("Ushbu test tugatilgan yoki boshlanmagan!", show_alert=True)
            return

        # Oxirgi javob berilmagan savolni topish (selected_option_index is NULL)
        unans_stmt = (
            select(StudentAnswer)
            .where(StudentAnswer.attempt_id == attempt.id, StudentAnswer.selected_option_index.is_(None))
            .order_by(StudentAnswer.order_index)
        )
        unans_res = await session.execute(unans_stmt)
        unans_list = unans_res.scalars().all()

        # Jami savollar sonini olish
        total_q_stmt = select(func.count(StudentAnswer.id)).where(
            StudentAnswer.attempt_id == attempt.id
        )
        total_q_res = await session.execute(total_q_stmt)
        total_q = total_q_res.scalar()

        if not unans_list:
            # Hamma savol javob berib bo'lingan, lekin yakunlanmagan
            last_q_idx = total_q
        else:
            last_q_idx = unans_list[0].order_index

    # FSM ni qayta tiklash
    await state.set_state(StudentStates.solving_quiz)
    await state.update_data(
        attempt_id=attempt.id,
        current_question_idx=last_q_idx,
        total_questions=total_q,
    )

    await callback.message.delete()
    await callback.answer()

    # Savolni ko'rsatish
    await show_student_question(callback.message.chat.id, state, callback.bot)
