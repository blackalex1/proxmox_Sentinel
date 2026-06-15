import logging
from aiogram import types
from aiogram.filters import BaseFilter
from core.config import settings

class AdminFilter(BaseFilter):
    """Глобальный фильтр: пропускает только администраторов из settings.admin_ids"""
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        user_id = event.from_user.id
        if not settings.admin_ids:
            logging.warning("access_attempt_from_but_admin_ids_is_not", user_id)
            return False
        return user_id in settings.admin_ids
