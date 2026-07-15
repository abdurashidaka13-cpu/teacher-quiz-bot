import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

# User ID lar bo'yicha oxirgi bosish vaqtlarini saqlash
THROTTLE_CACHE: Dict[int, float] = {}
THROTTLE_TIME = 0.6  # Cheklov vaqti (soniya)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Bot tugmalari va xabarlarini spam qilishga (DDoS) qarshi cheklov middleware.
    Foydalanuvchi belgilangan vaqtdan tezroq yozsa, xabarlarini o'tkazmaydi.
    """

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        # Foydalanuvchi Telegram ID sini olish
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id:
            now = time.time()
            last_time = THROTTLE_CACHE.get(user_id, 0)

            # Agar belgilangan vaqtdan tez bosilgan bo'lsa, ogohlantirish berish
            if now - last_time < THROTTLE_TIME:
                if isinstance(event, CallbackQuery):
                    # Tugmani bosganida ogohlantirish (alert shaklida)
                    await event.answer("Iltimos, shoshilmang! ⏳", show_alert=False)
                return  # Handlerga o'tkazmasdan to'xtatish

            # Cache-ni yangilash
            THROTTLE_CACHE[user_id] = now

        return await handler(event, data)
