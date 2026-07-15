import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from database import async_session, User, Subscription, SystemSettings
from config import local_now

router = Router()

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
        from states import AdminStates
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
            # Agar faqat ID berilsa, eski menyu chiqariladi
            from handlers.admin import process_mod_target
            await process_mod_target(message, user.id, state)
            return

        # Qolgan parametrlar: /mod [ident] [tickets] [max_students] [days]
        if len(args) >= 5:
            try:
                tickets = int(args[2])
                max_students = int(args[3])
                days = int(args[4])
            except ValueError:
                await message.answer("❌ Parametrlar noto'g'ri. Raqam bo'lishi kerak:\n/mod @username [tickets] [max_students] [days]")
                return

            user.role = "moderator"
            
            # Agar kun > 0 bo'lsa monthly, tickets > 0 bo'lsa onetime
            # Osonroq: agar days > 0 bo'lsa monthly obuna
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
                await message.answer(f"✅ Foydalanuvchiga muvaffaqiyatli huquqlar berildi!\n\nUser: {user.full_name}\nChiptalar: {tickets}\nPremium: {days} kun\nLimit: {max_students} o'quvchi.")
                try:
                    await bot.send_message(user.id, f"🎉 Admindan maxsus ruxsatlar berildi!\n\nChiptalar: {tickets} ta\nPremium: {days} kun\nO'quvchi limiti: {max_students} ta")
                except:
                    pass
            else:
                await message.answer("❌ Hech qanday ruxsat berilmadi (kun va chipta 0 bo'lsa).")

@router.message(Command("mod1"))
async def cmd_mod1(message: Message, bot: Bot):
    """/mod1 [ID yoki @username] - standart bir martalik chipta beradi."""
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
        
        await message.answer(f"✅ {user.full_name} ga 1 ta chipta berildi (Limit: {settings.onetime_max_students}).")
        try:
            await bot.send_message(user.id, f"🎉 Sizga 1 martalik test yaratish chiptasi berildi! (Limit: {settings.onetime_max_students} ta talaba)")
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

