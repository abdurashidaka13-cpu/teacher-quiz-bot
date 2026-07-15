import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
import pytz

# Loyiha bosh papkasini aniqlash
BASE_DIR = Path(__file__).resolve().parent

# .env faylini yuklash
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # Atrof-muhitdan o'qish (Render.com uchun)

# 1. Telegram Bot Tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("XATOLIK: BOT_TOKEN topilmadi! Iltimos, .env faylini tekshiring.")

# 2. Ma'lumotlar bazasi URL manzili (PostgreSQL)
# Neon.tech ba'zida postgres:// bilan beradi, SQLAlchemy asinxron ishlashi uchun postgresql+asyncpg:// shart.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("XATOLIK: DATABASE_URL topilmadi! Iltimos, .env faylini tekshiring.")

# Psycopg2 ga tegishli bo'lgan query parametrlarni (sslmode, channel_binding) asyncpg qo'llab-quvvatlamaydi,
# shuning uchun ularni olib tashlaymiz va keyinchalik ssl=True qilib ulanamiz.
if "?" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Ma'lumotlar bazasi SSL ulanish sozlamasi (mahalliy ishlab tushirish uchun)
DATABASE_SSL = os.getenv("DATABASE_SSL", "True").lower() == "true"

# 3. Super Admin Telegram ID raqamlari
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if admin_ids_raw:
    try:
        ADMIN_IDS = [int(aid.strip()) for aid in admin_ids_raw.split(",") if aid.strip()]
    except ValueError:
        print("OGOHLANTIRISH: ADMIN_IDS formatida xatolik bor, butun son bo'lishi kerak.")

# 4. Webhook Sozlamalari (Render.com uchun)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

# Xavfsiz webhook secret (agar env da belgilanmagan bo'lsa, bot tokendan dynamic generatsiya qilamiz)
import hashlib
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
if not WEBHOOK_SECRET:
    WEBHOOK_SECRET = hashlib.sha256((BOT_TOKEN + "QuizSecretSalt").encode()).hexdigest()

# Webhook faolligini aniqlash
USE_WEBHOOK = bool(WEBHOOK_URL)

# Webhook to'liq manzil (token oqib ketmasligi uchun tokenning SHA256 hashidan foydalanamiz)
token_hash = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()
WEBHOOK_PATH = f"/webhook/{token_hash}"
WEBHOOK_FULL_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}" if USE_WEBHOOK else ""

# 5. Server Porti
PORT = int(os.getenv("PORT", 8000))

# 6. Vaqt zonasi (Asia/Tashkent - O'zbekiston vaqti)
TIMEZONE = pytz.timezone("Asia/Tashkent")


def local_now() -> datetime.datetime:
    """O'zbekiston vaqti bilan xavfsiz offset-naive datetime qaytaradi"""
    return datetime.datetime.now(TIMEZONE).replace(tzinfo=None)


print("--- Loyiha Sozlamalari Yuklandi ---")
print(f"Baza turi: PostgreSQL Async (asyncpg)")
print(f"Super Adminlar soni: {len(ADMIN_IDS)} ta")
print(f"Webhook ishlatiladimi: {USE_WEBHOOK}")
if USE_WEBHOOK:
    print(f"Webhook URL: {WEBHOOK_FULL_URL}")
print(f"Vaqt zonasi: {TIMEZONE.zone}")
print("-----------------------------------")
