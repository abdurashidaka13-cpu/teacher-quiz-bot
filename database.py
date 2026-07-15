import datetime
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import pytz

from config import DATABASE_URL, TIMEZONE, local_now, DATABASE_SSL

# Async Engine yaratish
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"ssl": True} if DATABASE_SSL else {},
)

# Async Session maker
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# 1. Tizim Sozlamalari va Tarif Limitlari
class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    onetime_price: Mapped[int] = mapped_column(Integer, default=10000)  # 1 marta test narxi (so'm)
    monthly_price: Mapped[int] = mapped_column(Integer, default=50000)  # 1 oylik Premium narxi (so'm)
    demo_max_students: Mapped[int] = mapped_column(Integer, default=50)  # Demo student limiti
    onetime_max_students: Mapped[int] = mapped_column(Integer, default=50)  # 1 martalik student limiti
    monthly_max_students: Mapped[int] = mapped_column(Integer, default=50)  # Premium student limiti
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False)  # Texnik ishlar rejimi


# 2. Foydalanuvchilar (Adminlar va Moderatorlar)
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram ID
    full_name: Mapped[str] = mapped_column(String(100))
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="moderator")  # 'moderator', 'admin'
    referrer_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    referral_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=local_now
    )

    # Aloqalar (Relationship)
    quizzes: Mapped[List["Quiz"]] = relationship(
        "Quiz", back_populates="teacher", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )


# 3. Obunalar (Subscriptions)
class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(20))  # 'free_demo', 'onetime', 'monthly'
    credits: Mapped[int] = mapped_column(Integer, default=0)  # Foydalanish mumkin bo'lgan testlar soni (onetime uchun)
    expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)  # Oylik premium muddati
    max_students_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Shaxsiy o'quvchilar limiti
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=local_now
    )

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")


# 4. Testlar (Quizzes)
class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="waiting")  # 'waiting', 'active', 'completed'
    start_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    questions_to_show: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Har bir bolaga nechta savol chiqishi
    active_variants: Mapped[list] = mapped_column(JSONB, default=list)  # Faol variantlar, masalan: ['1', '2']
    code: Mapped[str] = mapped_column(String(10), unique=True)  # Testga kirish kodi (masalan: 582910)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=local_now
    )

    # Aloqalar
    teacher: Mapped["User"] = relationship("User", back_populates="quizzes")
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="quiz", cascade="all, delete-orphan"
    )
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="quiz", cascade="all, delete-orphan"
    )


# 5. Savollar (Questions)
class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"))
    question_text: Mapped[str] = mapped_column(Text)
    image_data: Mapped[Optional[bytes]] = mapped_column(BYTEA, nullable=True)  # Siqilgan WebP rasm binary
    correct_answer: Mapped[str] = mapped_column(Text)
    distractors: Mapped[list] = mapped_column(JSONB)  # 3 ta noto'g'ri javob ro'yxati
    variant: Mapped[str] = mapped_column(String(50), default="1")  # Variant nomi, masalan: "Variant 1"

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")
    answers: Mapped[List["StudentAnswer"]] = relationship(
        "StudentAnswer", back_populates="question", cascade="all, delete"
    )


# 6. Studentlar (Students - Vaqtinchalik sessiyalar bilan)
class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("quiz_id", "login", name="uq_quiz_login"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(150))
    login: Mapped[str] = mapped_column(String(100))
    password: Mapped[str] = mapped_column(String(100))
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # Vaqtinchalik sessiya ID si
    logged_in_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="students")
    attempts: Mapped[List["StudentAttempt"]] = relationship(
        "StudentAttempt", back_populates="student", cascade="all, delete-orphan"
    )


# 7. Student imtihon urinishlari (Student Attempts)
class StudentAttempt(Base):
    __tablename__ = "student_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id", ondelete="CASCADE"))
    score: Mapped[int] = mapped_column(Integer, default=0)  # To'g'ri topilgan javoblar soni
    total_questions: Mapped[int] = mapped_column(Integer, default=0)  # Jami topshirilgan savollar
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=local_now
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    student: Mapped["Student"] = relationship("Student", back_populates="attempts")
    answers: Mapped[List["StudentAnswer"]] = relationship(
        "StudentAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )


# 8. Student javoblari (Shuffled and logged answers)
class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey("student_attempts.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))
    order_index: Mapped[int] = mapped_column(Integer)  # O'quvchiga berilgan tartib raqami (1 dan m gacha)
    shuffled_options: Mapped[list] = mapped_column(JSONB)  # Chalkashtirilgan variantlar ro'yxati (masalan: ['B', 'A', 'D', 'C'])
    selected_option_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Tanlagan varianti (0-3 indeks)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    attempt: Mapped["StudentAttempt"] = relationship("StudentAttempt", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")


# Ma'lumotlar bazasini ishga tushirish (jadvallarni yaratish)
async def init_db():
    print("Ma'lumotlar bazasi jadvallari tekshirilmoqda/yaratilmoqda...")
    async with engine.begin() as conn:
        # Debug paytida jadvallarni o'chirish kerak bo'lsa:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
        # Migratsiya: users jadvaliga referal ustunlarini qo'shish
        from sqlalchemy import text
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_id BIGINT REFERENCES users(id) ON DELETE SET NULL;"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_count INTEGER DEFAULT 0;"))
        except Exception as e:
            # SQLite yoki eski Postgres da xato berishi mumkin, ikkinchi urinish
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN referrer_id BIGINT;"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0;"))
            except Exception:
                pass
    print("Baza jadvallari muvaffaqiyatli tekshirildi.")

    # Boshlang'ich tizim sozlamalarini yaratish
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(SystemSettings))
        settings = result.scalar_one_or_none()
        if not settings:
            new_settings = SystemSettings()
            session.add(new_settings)
            await session.commit()
            print("Standart tizim sozlamalari (SystemSettings) bazaga kiritildi.")
