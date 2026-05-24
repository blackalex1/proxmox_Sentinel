import logging
from aiogram import types
from aiogram.filters import BaseFilter
from core.config import ADMIN_IDS

class AdminFilter(BaseFilter):
    """Глобальный фильтр: пропускает только администраторов из ADMIN_IDS"""
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        user_id = event.from_user.id
        if not ADMIN_IDS:
            logging.warning(f"🚨 Попытка доступа от {user_id}, но ADMIN_IDS не настроен в .env! Доступ запрещен.")
            return False
        return user_id in ADMIN_IDS
