import asyncio
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, HTTPException, status
from uvicorn import run
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from sqlalchemy import select, delete

import config
import os
from config import BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_PATH, TIMEZONE, local_now
from database import init_db, async_session, User, Subscription, Quiz, Student, StudentAttempt, StudentAnswer
from utils.throttling import ThrottlingMiddleware
from handlers import common, teacher, student, admin
import logging

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(token=BOT_TOKEN)

# FSM Storage ni tanlash (Redis bo'lsa Redis, aks holda Memory)
redis_url = os.getenv("REDIS_URL")
storage = MemoryStorage()

if redis_url:
    try:
        from aiogram.fsm.storage.redis import RedisStorage
        storage = RedisStorage.from_url(redis_url)
        logger.info("FSM Storage: Redis faol [OK]")
    except ImportError:
        logger.warning("FSM Storage: 'redis' kutubxonasi o'rnatilmagan! MemoryStorage ishlatilmoqda.")
else:
    logger.warning("FSM Storage: MemoryStorage faol (ogohlantirish: restartda o'chib ketadi)")

dp = Dispatcher(storage=storage)

# Middleware va Routerlarni ulash
dp.message.middleware(ThrottlingMiddleware())
dp.callback_query.middleware(ThrottlingMiddleware())

dp.include_router(common.router)
dp.include_router(teacher.router)
dp.include_router(student.router)
dp.include_router(admin.router)


# ==========================================
# AVTOMATIK BAZANI TOZALASH FUNKSIYASI (CLEANUP)
# ==========================================
async def run_database_cleanup():
    """
    30 kundan beri ishlatilmagan Demo va muddati tugagan (Expired)
    moderatorlar va ularning testlarini (rasmlari bilan kaskad) o'chiradi.
    """
    now = local_now()
    cutoff = now - datetime.timedelta(days=30)
    logger.info(f"[BAZA CLEANUP] Tozalash ishlari boshlandi (Cutoff: {cutoff})...")

    async with async_session() as session:
        try:
            # 1. 30 kundan ko'p vaqt oldin muddati tugagan oylik obunachilar
            expired_sub_stmt = select(Subscription.user_id).where(
                Subscription.type == "monthly",
                Subscription.expires_at < cutoff,
            )
            expired_users = (await session.execute(expired_sub_stmt)).scalars().all()

            # 2. 30 kundan beri test yuklamagan yoki nofaol bo'lgan Demo moderatorlar
            demo_stmt = (
                select(User.id)
                .join(Subscription)
                .where(
                    User.role == "moderator",
                    Subscription.type == "free_demo",
                    User.created_at < cutoff,
                )
            )
            inactive_demo_users = (await session.execute(demo_stmt)).scalars().all()

            # Jami o'chiriladigan ID lar
            target_ids = list(set(expired_users + inactive_demo_users))

            if target_ids:
                # Kaskad o'chirish (Foreign Key ondelete='CASCADE' o'zi bog'liq jadvallarni tozalaydi)
                del_stmt = delete(User).where(User.id.in_(target_ids))
                await session.execute(del_stmt)
                await session.commit()
                logger.info(f"[BAZA CLEANUP] Muvaffaqiyatli yakunlandi. Jami o'chirilgan nofaol profillar: {len(target_ids)} ta.")
            else:
                logger.info("[BAZA CLEANUP] O'chiriladigan nofaol profillar topilmadi.")
        except Exception as e:
            logger.error(f"[BAZA CLEANUP] Tozalashda xatolik: {e}")


async def scheduled_quiz_auto_close():
    """Har 1 daqiqada vaqti tugagan testlarni avtomatik yopadi"""
    import asyncio
    while True:
        await asyncio.sleep(60)  # Har 1 daqiqada tekshirish
        try:
            now = local_now()
            async with async_session() as session:
                # Vaqti tugagan faol testlarni topish
                stmt = select(Quiz).where(Quiz.status == "active", Quiz.end_time <= now)
                quizzes = (await session.execute(stmt)).scalars().all()
                
                for quiz in quizzes:
                    quiz.status = "completed"
                    
                    # Talabalarni topish va yakunlash
                    students = (await session.execute(select(Student).where(Student.quiz_id == quiz.id))).scalars().all()
                    for s in students:
                        # Faol telegram foydalanuvchilariga xabar yuborish uchun ID saqlaymiz
                        tg_id = s.telegram_id
                        
                        # Urinishni yakunlash
                        att_stmt = select(StudentAttempt).where(
                            StudentAttempt.student_id == s.id, StudentAttempt.completed_at.is_(None)
                        )
                        attempt = (await session.execute(att_stmt)).scalar_one_or_none()
                        
                        if attempt:
                            attempt.completed_at = quiz.end_time
                            answers = (await session.execute(select(StudentAnswer).where(StudentAnswer.attempt_id == attempt.id))).scalars().all()
                            correct_count = sum(1 for a in answers if a.is_correct)
                            attempt.score = correct_count
                            attempt.total_questions = len(answers)
                            
                        # Auto logout
                        s.telegram_id = None
                        
                        if tg_id:
                            try:
                                await bot.send_message(
                                    tg_id,
                                    "🛑 **Imtihon vaqti tugadi!**\nTizimdan avtomat chiqdingiz (Logout). Natijangiz saqlandi."
                                )
                            except Exception:
                                pass
                                
                    await session.commit()
                    logger.info(f"[AUTO CLOSE] Test yopildi: {quiz.title} (ID: {quiz.id})")
                    
        except Exception as e:
            logger.error(f"[AUTO CLOSE TASK] Xatolik: {e}")


async def scheduled_database_cleanup():
    """Har 24 soatda avtomatik tozalash ishlarini bajaradi"""
    import asyncio
    while True:
        await asyncio.sleep(86400)  # 24 soat kutish
        try:
            await run_database_cleanup()
        except Exception as e:
            logger.error(f"[BAZA CLEANUP TASK] Rejali tozalashda xatolik: {e}")


# ==========================================
# FASTAPI LIFESPAN (KIRISH VA SHUTDOWN)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Ma'lumotlar bazasi jadvallarini tekshirish va yaratish
    await init_db()

    # 2. Mavsumiy tozalashni ishga tushirish (startupda 1 marta va har 24 soatda orqa fonda)
    await run_database_cleanup()
    asyncio.create_task(scheduled_database_cleanup())
    asyncio.create_task(scheduled_quiz_auto_close())

    # 3. Webhook yoki Polling sozlash
    if config.USE_WEBHOOK:
        # Render webhook ulanishini sozlash
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url != config.WEBHOOK_FULL_URL:
            await bot.set_webhook(
                url=config.WEBHOOK_FULL_URL,
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
                secret_token=config.WEBHOOK_SECRET,
            )
        logger.info(f"Webhook o'rnatildi: {config.WEBHOOK_FULL_URL}")
    else:
        # Polling rejimida orqa fonda ishga tushirish (Lokal kompyuter uchun)
        logger.info("Bot Polling rejimida ishga tushmoqda...")
        asyncio.create_task(dp.start_polling(bot))

    yield

    # Shutdown hodisasi (Webhook o'chirish bekor qilindi, rolling redeploy muammosi tufayli)
    # if config.USE_WEBHOOK:
    #     logger.info("Webhook o'chirilmoqda...")
    #     await bot.delete_webhook(drop_pending_updates=True)
    
    await bot.session.close()
    logger.info("Bot to'xtatildi.")


# FastAPI ilovasi
app = FastAPI(lifespan=lifespan)


# ==========================================
# WEBHOOK ENDPOINT (Render.com uchun)
# ==========================================
@app.post(WEBHOOK_PATH)
async def webhook_endpoint(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    """Telegram webhook so'rovlarini qabul qiluvchi endpoint"""
    # DDoS va soxtalashtirishga qarshi Secret Token tekshiruvi
    if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Taqiqlangan so'rov (Yaroqsiz Secret Token)",
        )

    try:
        # So'rovni Update formatiga o'tkazish va dispatch qilingan handlerga yuborish
        request_json = await request.json()
        update = Update.model_validate(request_json, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"[WEBHOOK ERROR] So'rovga ishlov berishda xato: {e}")

    return {"status": "ok"}


# Health Check (Render.com bekor turib o'chib qolmasligi uchun kerak)
@app.get("/health")
async def health_check():
    return {"status": "healthy", "time": str(datetime.datetime.now())}


# FastAPI ni ishga tushirish (Lokal ishlatilganda)
if __name__ == "__main__":
    run(app, host="0.0.0.0", port=config.PORT)
